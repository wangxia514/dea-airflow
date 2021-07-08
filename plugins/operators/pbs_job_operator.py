"""
This module defines an Airflow Operator for submitting and monitoring PBS jobs
on a remote host.

Previously we have combined SSHOperator + PBSJobCompleteSensor, linked via Airflow
xcom to submit and monitor PBS jobs.

There are several drawbacks to this approach.
- It's a more complicated structure when setting up the dag.
- There's extra boilerplate for the job submission that could be hidden.
- When a job fails, it's necessary to 'clear' the submission task, not the monitoring
  task, which is somewhat counter intuitive.
- The runtime of the job is harder to gauge

Extra Features
- Easier to use
- Able to pull PBS job logs, or at least the end of them, into the airflow logs
- (maybe) better able to handle failures.

"""

import json
from logging import getLogger

from airflow import AirflowException
from airflow.sensors.base_sensor_operator import BaseSensorOperator

from dea_airflow_common.ssh import SSHRunMixin

log = getLogger(__name__)


# Putting the SSHMixin first, so that it hopefully consumes it's __init__ arguments
class PBSJobOperator(SSHRunMixin, BaseSensorOperator):

    # TODO, how do we handle work_dir?
    # - Is it okay to ignore?
    # - Is it another required argument?

    template_fields = ("pbs_args", "pbs_command",)
    @apply_defaults
    def __init__(
            self,

            qsub_args: str,
            qsub_command: str,
            work_dir: str,
            poke_interval: int = 5 * 60,
            mode="reschedule",
            timeout: int = 24 * 60 * 60,
            *args,
            **kwargs,

    ):
        super().__init__(
            mode=mode,
            poke_interval=poke_interval,
            timeout=timeout,
            *args,
            **kwargs
        )
        self.log.info("Inside PBSJobOperator __init__")
        self.qsub_args = qsub_args
        self.qsub_command = qsub_command
        self.work_dir = work_dir
        self.pbs_job_id = None

    def execute(self, context):
        if self.pbs_job_id:
            # If we have submitted a job already, delegate to the poke() function via BaseSensorOperator
            # Which handles rescheduling and re-executing as required.
            super().execute(context)
        else:
            # Running for the first time, submit the job
            ret_val, output = self.run_ssh_command_and_return_output(
                f"""
          mkdir -p { self.work_dir };
          cd { self.work_dir };
          qsub \
          {self.qsub_args} \
          -o { self.work_dir } -e { self.work_dir }
          -- {self.qsub_command}
                """
            )
            if ret_val == 0:
                self.pbs_job_id = output.strip()
            else:
                raise AirflowException("Error submitting PBS Job")

    def poke(self, context):
        # qstat json output incorrectly attempts to escape single quotes
        # This can be fixed with sed, or within python, sed  "s/\\\'/'/g"

        try:
            ret_val, output = self.run_ssh_command_and_return_output(
                f"qstat -fx -F json {self.pbs_job_id}"
            )
        except EOFError:
            # Sometimes qstat hangs and doesn't complete it's output. Be accepting of this,
            # and simply try again next Sensor interval.
            self.log.exception("Failed getting output from qstat")
            return False

        # PBS returns incorrectly escaped JSON. Patch it.
        output = output.replace("'", "'")
        try:
            result = json.loads(output)
        except json.JSONDecodeError as e:
            self.log.exception("Error parsing qstat output: ", exc_info=e)
            return False

        job_state = result["Jobs"][self.pbs_job_id]["job_state"]
        if job_state == "F":
            pbs_result = result["Jobs"][self.pbs_job_id]
            exit_status = pbs_result["Exit_status"]

            self.xcom_push(context, "return_value", pbs_result)

            if exit_status == 0:
                return True
            else:
                # TODO: I thought this would stop retries, but it doesn't. We need to either set
                # retry to 0, or do something fancy here, since
                # https://github.com/apache/airflow/pull/7133 isn't implemented yet.
                # The only way to /not/ retry is by setting the `task_instance.max_tries = 0`
                # as seen here: https://gist.github.com/robinedwards/3f2ec4336e1ced084547d24d7e7ead3a
                raise AirflowException("PBS Job Failed %s", self.pbs_job_id)
        else:
            return False
