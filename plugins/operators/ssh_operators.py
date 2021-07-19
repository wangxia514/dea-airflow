"""
DEA Airflow SSH Operators

"""
import os.path
from base64 import b64encode

from io import StringIO

from airflow import AirflowException
from airflow.configuration import conf
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.providers.sftp.operators.sftp import _make_intermediate_dirs
from airflow.models import BaseOperator, SkipMixin
from airflow.utils.decorators import apply_defaults

from dea_airflow_common.ssh import SSHRunMixin


class SecretHandlingSSHOperator(SSHRunMixin, BaseOperator):
    template_fields = ('command', 'secret_command')

    @apply_defaults
    def __init__(self,
                 command: str = None,
                 secret_command: str = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = command
        self.secret_command = secret_command

    def execute(self, context):
        command = self.command
        if self.secret_command:
            # This works on gadi but fails with GitHub Actions + pytest + mockssh
            # command = '. /dev/stdin; ' + self.command
            command = 'eval "$(cat -)"; ' + self.command

        exit_status, output = self.run_ssh_command_and_return_output(command, self.secret_command)

        if exit_status == 0:
            # returning output if do_xcom_push is set
            if self.do_xcom_push:
                enable_pickling = conf.getboolean(
                    'core', 'enable_xcom_pickling'
                )
                if enable_pickling:
                    return output
                else:
                    return b64encode(output).decode('utf-8')

        else:
            error_msg = output
            raise AirflowException("error running cmd: {0}, error: {1}"
                                   .format(self.command, error_msg))

        return True


class ShortCircuitSSHOperator(SSHRunMixin, BaseOperator, SkipMixin):
    """
    Execute an SSH command and then Optionally Short Circuit

    The condition is determined by the return value of running `command`
    on the provided SSH host..
    """

    template_fields = ("command",)

    @apply_defaults
    def __init__(self, command: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = command

    def execute(self, context):
        ret_val, output = self.run_ssh_command_and_return_output(self.command)
        self.log.info("SSH command return value is %s", ret_val)

        if ret_val == 0:
            self.log.info("Proceeding with downstream tasks...")
            return

        self.log.info("Skipping downstream tasks...")

        downstream_tasks = context["task"].get_flat_relatives(upstream=False)
        self.log.debug("Downstream task_ids %s", downstream_tasks)

        if downstream_tasks:
            self.skip(
                context["dag_run"], context["ti"].execution_date, downstream_tasks
            )

        self.log.info("Done.")


class TemplateToSFTPOperator(BaseOperator):
    """
    TemplateToSFTPOperator is for uploading a file to a remote server
    based on a template. It takes many of the same params as SFTPOperator.

    :param str ssh_conn_id: connection id from airflow Connections.
        `ssh_conn_id` will be ignored if `ssh_hook` is provided.
    :param bool create_intermediate_dirs: create missing intermediate directories when
        copying from remote to local and vice-versa. Default is False.
    :param int file_mode: permissions to set on the remote file. eg 0o644 or 0o755
    :param file_contents: contents to upload into the file (templated)
    :param remote_filepath: remote file path to get or put. (templated)
    """

    template_fields = ("file_contents", "remote_filepath")
    template_ext = ("jinja2",)

    @apply_defaults
    def __init__(
        self,
        ssh_conn_id=None,
        ssh_hook=None,
        file_mode=None,
        file_contents="",
        remote_filepath=None,
        create_intermediate_dirs=True,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.ssh_hook = ssh_hook
        self.ssh_conn_id = ssh_conn_id
        self.file_mode = file_mode
        self.file_contents = file_contents
        self.remote_filepath = remote_filepath
        self.create_intermediate_dirs = create_intermediate_dirs

    def execute(self, context):
        try:
            if self.ssh_conn_id:
                if self.ssh_hook and isinstance(self.ssh_hook, SSHHook):
                    self.log.info("ssh_conn_id is ignored when ssh_hook is provided.")
                else:
                    self.log.info(
                        "ssh_hook is not provided or invalid. "
                        + "Trying ssh_conn_id to create SSHHook."
                    )
                    self.ssh_hook = SSHHook(ssh_conn_id=self.ssh_conn_id)

            if not self.ssh_hook:
                raise AirflowException(
                    "Cannot operate without ssh_hook or ssh_conn_id."
                )

            with self.ssh_hook.get_conn() as ssh_client:
                sftp_client = ssh_client.open_sftp()

                remote_folder = os.path.dirname(self.remote_filepath)
                if self.create_intermediate_dirs:
                    _make_intermediate_dirs(
                        sftp_client=sftp_client, remote_directory=remote_folder
                    )
                self.log.info("Starting to transfer file to %s", self.remote_filepath)

                file_contents_fo = StringIO(self.file_contents)
                sftp_client.putfo(file_contents_fo, self.remote_filepath)

                if self.file_mode is not None:
                    sftp_client.chmod(self.remote_filepath, self.file_mode)
        except Exception as e:
            raise AirflowException(
                "Error while uploading to {0}, error: {1}".format(
                    self.remote_filepath, str(e)
                )
            )

        return self.remote_filepath
