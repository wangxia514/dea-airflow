"""
This module defines a Helper mixin class for running commands
over SSH Connections.

TODO: It would probably make sense to integrate this into a new SSHHook
TODO: And then try to push it upstream as it's useful functionality
"""
from select import select

from airflow import AirflowException
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.utils.decorators import apply_defaults


class SSHRunMixin:
    """Mixin class to use when defining a new Airflow Operator that operates over SSH"""

    @apply_defaults
    def __init__(self, ssh_conn_id=None, ssh_hook=None, timeout=10, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log.info("Inside SSHRunMixin Init Function")
        self.timeout = timeout
        self.ssh_hook = ssh_hook
        self.ssh_conn_id = ssh_conn_id

    def run_ssh_command_and_return_output(self, command, stdin_data=None) -> (int, str):
        """
        Open and SSH Connection and execute a command

        Also allows feeding a string to stdin.

        Returns the exit status and output from stdout
        """
        # Copied from ssh_operator.py . It's not reusable from there.
        try:
            if self.ssh_conn_id:
                if self.ssh_hook and isinstance(self.ssh_hook, SSHHook):
                    self.log.info("ssh_conn_id is ignored when ssh_hook is provided.")
                else:
                    self.log.info(
                        "ssh_hook is not provided or invalid. "
                        + "Trying ssh_conn_id to create SSHHook."
                    )
                    self.ssh_hook = SSHHook(
                        ssh_conn_id=self.ssh_conn_id, timeout=self.timeout
                    )

            if not self.ssh_hook:
                raise AirflowException(
                    "Cannot operate without ssh_hook or ssh_conn_id."
                )

            if not command:
                raise AirflowException("SSH command not specified. Aborting.")

            with self.ssh_hook.get_conn() as ssh_client:
                self.log.info("Running command: %s", command)

                # set timeout taken as params
                stdin, stdout, stderr = ssh_client.exec_command(
                    command=command, get_pty=False, timeout=self.timeout
                )

                if stdin_data:
                    stdin.write(stdin_data)
                # get channels
                channel = stdout.channel

                # closing stdin
                stdin.close()
                channel.shutdown_write()

                agg_stdout = b""
                agg_stderr = b""

                # capture any initial output in case channel is closed already
                stdout_buffer_length = len(stdout.channel.in_buffer)

                if stdout_buffer_length > 0:
                    agg_stdout += stdout.channel.recv(stdout_buffer_length)

                # read from both stdout and stderr
                while (
                    not channel.closed
                    or channel.recv_ready()
                    or channel.recv_stderr_ready()
                ):
                    readq, _, _ = select([channel], [], [], self.timeout)
                    for c in readq:
                        if c.recv_ready():
                            line = stdout.channel.recv(len(c.in_buffer))
                            line = line
                            agg_stdout += line
                            self.log.info(line.decode("utf-8").strip("\n"))
                        if c.recv_stderr_ready():
                            line = stderr.channel.recv_stderr(len(c.in_stderr_buffer))
                            line = line
                            agg_stderr += line
                            self.log.warning(line.decode("utf-8").strip("\n"))
                    if (
                        stdout.channel.exit_status_ready()
                        and not stderr.channel.recv_stderr_ready()
                        and not stdout.channel.recv_ready()
                    ):
                        stdout.channel.shutdown_read()
                        stdout.channel.close()
                        break

                stdout.close()
                stderr.close()

                exit_status = stdout.channel.recv_exit_status()

                return exit_status, agg_stdout.decode("utf-8")
        except EOFError:
            raise
        except Exception as e:
            raise AirflowException("SSH error: {0}".format(str(e)))
