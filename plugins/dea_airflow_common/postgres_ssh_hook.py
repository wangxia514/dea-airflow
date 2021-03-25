import logging

import psycopg2
from airflow.hooks.postgres_hook import PostgresHook

LOG = logging.getLogger(__name__)


class PostgresSSHHook(PostgresHook):
    """

    """

    def __init__(self, ssh_hook, *args, **kwargs):
        super(PostgresSSHHook, self).__init__(*args, **kwargs)
        self.ssh_hook = ssh_hook
        self.tunnel = None

    def get_conn(self):
        conn_id = getattr(self, self.conn_name_attr)
        conn = self.get_connection(conn_id)

        if self.tunnel is None:
            self.tunnel = self.ssh_hook.get_tunnel(remote_port=conn.port, remote_host=conn.host)

            self.tunnel.start()

        LOG.info(f"Connected SSH Tunnel: {self.tunnel}")
        # Airflow conflates dbname and schema, even though they are very different in PG

        conn_args = dict(
            host='localhost',
            user=conn.login,
            password=conn.password,
            dbname=self.schema or conn.schema,
            port=self.tunnel.local_bind_port)
        raw_cursor = conn.extra_dejson.get('cursor', False)
        if raw_cursor:
            conn_args['cursor_factory'] = self._get_cursor(raw_cursor)
        # check for ssl parameters in conn.extra
        for arg_name, arg_val in conn.extra_dejson.items():
            if arg_name in ['sslmode', 'sslcert', 'sslkey',
                            'sslrootcert', 'sslcrl', 'application_name',
                            'keepalives_idle']:
                conn_args[arg_name] = arg_val

        # It's important to wrap this connection in a try/finally block, otherwise
        # we can cause a deadlock with the SSHTunnel
        conn = psycopg2.connect(**conn_args)
        return conn

    def close(self):
        self.tunnel.stop()
        self.tunnel = None
