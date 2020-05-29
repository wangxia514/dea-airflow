"""
Implements an Airflow Sensor for awaiting the completion of a PBS Job
"""
import json
from base64 import b64decode
from json import JSONDecodeError
from logging import getLogger

from airflow import AirflowException
from airflow.configuration import conf
from airflow.sensors.base_sensor_operator import BaseSensorOperator
from airflow.utils.decorators import apply_defaults

from dea_airflow_common.ssh import SSHRunMixin

log = getLogger(__name__)


def maybe_decode_xcom(data):
    """Prepare XCom data passed from an SSHOperator

    If pickling of XCom values is disabled (optional setting now, but the
    default come Airflow 2.0) The SSHOperator will base64 encode output stored
    in XCOM.

    This function does the reverse of code in the SSHOperator
    """
    enable_pickling = conf.getboolean("core", "enable_xcom_pickling")
    if enable_pickling:
        return data.strip()
    else:
        return b64decode(data).decode('utf8').strip()


# Putting the SSHMixin first, so that it hopefully consumes it's __init__ arguments
class PBSJobSensor(SSHRunMixin, BaseSensorOperator):
    """
    Wait for completion of a PBS job on a remote SSH host.

    :param pbs_job_id: The PBS Job Id to await completion of (templated)
    :type pbs_job_id: str
    """
    template_fields = ('pbs_job_id',)

    @apply_defaults
    def __init__(self,
                 pbs_job_id: str = None,
                 poke_interval: int = 5 * 60,
                 mode='reschedule',
                 timeout: int = 24 * 60 * 60,
                 *args, **kwargs):
        super().__init__(mode=mode, poke_interval=poke_interval, timeout=timeout, *args, **kwargs)
        self.log.info('Inside PBSJobSensor Init Function')

        self.pbs_job_id = maybe_decode_xcom(pbs_job_id)
        self.log.info('Using pbs_job_id: %s', self.pbs_job_id)

    def poke(self, context):
        # qstat json output incorrectly attempts to escape single quotes
        # This can be fixed with sed, or within python, sed  "s/\\\'/'/g"
        pbs_job_id = self.pbs_job_id
        if pbs_job_id.endswith('='):
            self.pbs_job_id = b64decode(pbs_job_id).decode('utf8').strip()
            self.log.info('Decoding pbs_job_id to: %s', self.pbs_job_id)
        else:
            # Lets trust the value given
            self.pbs_job_id = pbs_job_id
            self.log.info('Trusting given pbs_job_id: %s', self.pbs_job_id)

        try:
            ret_val, output = self.run_ssh_command_and_return_output(f'qstat -fx -F json {self.pbs_job_id}')
        except EOFError:
            # Sometimes qstat hangs and doesn't complete it's output. Be accepting of this,
            # and simply try again next Sensor interval.
            self.log.exception('Failed getting output from qstat')
            return False

        # PBS returns incorrectly escaped JSON. Patch it.
        output = output.replace("\'", "'")
        try:
            result = json.loads(output)
        except JSONDecodeError as e:
            self.log.exception("Error parsing qstat output: ", exc_info=e)
            return False

        job_state = result['Jobs'][self.pbs_job_id]['job_state']
        if job_state == 'F':
            exit_status = result['Jobs'][self.pbs_job_id]['Exit_status']
            if exit_status == 0:
                context['ti'].xcom_push(key='pbs_job_id', value=self.pbs_job_id)
                return True
            else:
                # TODO: I thought this would stop retries, but it doesn't. We need to either set
                # retry to 0, or do something fancy here, since
                # https://github.com/apache/airflow/pull/7133 isn't implemented yet.
                # The only way to /not/ retry is by setting the `task_instance.max_tries = 0`
                # as seen here: https://gist.github.com/robinedwards/3f2ec4336e1ced084547d24d7e7ead3a
                raise AirflowException('PBS Job Failed %s', self.pbs_job_id)
        else:
            return False
