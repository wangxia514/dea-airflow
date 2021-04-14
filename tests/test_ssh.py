import mockssh
from airflow.contrib.hooks.ssh_hook import SSHHook

from pathlib import Path
from unittest.mock import MagicMock
import pytest
import paramiko

from operators.ssh_operators import ShortCircuitSSHOperator, SecretHandlingSSHOperator


@pytest.fixture
def ssh_key_file(tmp_path):
    key = paramiko.RSAKey.generate(4096)
    pub_key = tmp_path / 'id_rsa.pub'
    private_key = tmp_path / 'id_rsa'
    pub_key.write_text(key.get_base64())  # save public key
    with private_key.open(mode='w') as fout:
        key.write_private_key(fout)  # save private key

    yield pub_key, private_key


@pytest.fixture
def server(ssh_key_file):
    _, private_key = ssh_key_file
    users = {
        "test-user": str(private_key),
    }
    with mockssh.Server(users) as s:
        yield s


def test_ssh_server_fixture(server):
    for uid in server.users:
        with server.client(uid) as c:
            _, stdout, _ = c.exec_command("ls /")
            output = stdout.read().decode('utf-8')
            assert output
            assert 'usr' in output


def test_secret_handling_ssh_operator_without_secret(server: mockssh.Server):
    for uid in server.users:
        private_key_path, _ = server._users[uid]
        hook = SSHHook(remote_host=server.host, port=server.port, username=uid, key_file=private_key_path)
        operator = SecretHandlingSSHOperator(task_id='test', ssh_hook=hook, command='echo hello', do_xcom_push=True)
        output = operator.execute(None)
        assert 'hello' in output


def test_secret_handling_ssh_operator(server: mockssh.Server):
    for uid in server.users:
        private_key_path, _ = server._users[uid]
        hook = SSHHook(remote_host=server.host, port=server.port, username=uid, key_file=private_key_path)
        operator = SecretHandlingSSHOperator(task_id='test',
                                             ssh_hook=hook,
                                             command='echo $FOOBAR',
                                             secret_command='export FOOBAR=hello-world;\n',
                                             do_xcom_push=True)
        output = operator.execute(None)
        assert 'hello-world' in output


def test_short_circuit_ssh_operator(server, monkeypatch):
    skipped = False
    def mock_skip(dagrun, execution_date, downstream_tasks):
        nonlocal skipped
        skipped = True

    class MockTask:
        def get_flat_relatives(self, upstream=False):
            return ['hello']
    class MockTaskInstance:
        execution_date = None

    for uid in server.users:
        private_key_path, _ = server._users[uid]
        hook = SSHHook(remote_host=server.host, port=server.port, username=uid, key_file=private_key_path)
        operator = ShortCircuitSSHOperator(task_id='test',
                                           ssh_hook=hook,
                                           command='false')

        mock_context = {'task': MockTask(), 'dag_run': None, 'ti': MockTaskInstance()}

        monkeypatch.setattr(operator, 'skip', mock_skip)

        output = operator.execute(mock_context)
        assert skipped
