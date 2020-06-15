import logging

from psycopg2.extras import Json
import psycopg2
import requests
from airflow import DAG
from airflow import secrets
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator

LOG = logging.getLogger(__name__)

repos = [
    ("opendatacube", "datacube-core"),
    ("opendatacube", "datacube-stats"),
    ("opendatacube", "datacube-explorer"),
    ("opendatacube", "datacube-ows"),
    ("opendatacube", "dea-proto"),
    ("GeoscienceAustralia", "digitalearthau"),
]


def _record_statistics(ts, postgres_conn_id, ssh_conn_id, **context):
    # Can't use PostgresHook because our TCP port is likely to be dynamic
    # because we are connecting through an SSH Tunnel
    pg_secret = secrets.get_connections(postgres_conn_id)

    ssh_conn = SSHHook(ssh_conn_id=ssh_conn_id)
    tunnel = ssh_conn.get_tunnel(remote_port=pg_secret.port, remote_host=pg_secret.host)

    stats_retriever = GitHubStatsRetriever()

    with tunnel:
        conn = psycopg2.connect(f"host=localhost "
                                "user={pg_secret.login} "
                                "port={tunnel.local_bind_port} "
                                "password={pg_secret.password}")

        ensure_pg_table(conn)

        for owner, repo in repos:
            stats = stats_retriever.get_repo_stats(owner, repo)

            save_record_to_pg(conn, ts, f'{owner}/{repo}', stats)


def ensure_pg_table(conn):
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS gh_metrics_raw (
    timestamp timestamp,
    repo text,
    data jsonb,
    PRIMARY KEY (timestamp, repo));""")
    cur.close()

def save_record_to_pg(conn, timestamp, repo, record):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gh_metrics_raw (timestamp, repo, data) VALUES(%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, [timestamp, repo, Json(record)])
    cur.close()


dag = DAG(
    dag_id='github_metrics',
    start_date='2020-06-15'
)


with dag:
    record_statistics = PythonOperator(
        task_id='record_statistics',
        python_callable=_record_statistics,
        params=dict(postgres_conn_id='lpgs_pg',
                    ssh_conn_id='lpgs_gadi'
        ),
        provide_context=True
    )

class GitHubStatsRetriever:
    """
    Retrieve stats about GitHub repositories

    :param string token: GitHub Authentication Token
    """

    def __init__(self, token):
        self.token = token

    def get_repo_stats(self, owner, repo):
        """
        Retrieve combined Fundamental and Traffic Stats
        :param owner:
        :param repo:
        :return:
        """
        stats = self.get_graphql_stats(owner, repo)

        stats['traffic'] = self.get_repo_traffic(owner, repo)

        return stats

    def get_graphql_stats(self, owner, repo):
        # language=GraphQL
        query = '''
            query RepoStats($owner: String!, $repo: String!) {
              repository(owner:$owner, name:$repo) {
                name
                nameWithOwner
                id
                diskUsage
                forkCount
                pushedAt
                stargazers {
                  totalCount
                }
                watchers {
                  totalCount
                }
                issues {
                  totalCount
                }
                openIssues: issues(states:OPEN) {
                  totalCount
                }
                closedIssues: issues(states:CLOSED) {
                  totalCount
                }
                pullRequests {
                  totalCount
                }
                openPullRequests: pullRequests(states:OPEN) {
                  totalCount
                }
                branches: refs(refPrefix: "refs/heads/") {
                  totalCount
                }
                collaborators { totalCount }
                releases { totalCount }
                commits: object(expression:"develop") {
                  ... on Commit {
                    history {
                      totalCount
                    }
                  }
                }
              }
            }
        '''
        variables = {
            "owner": owner,
            "repo": repo
        }

        response = self.gh_graphql_query(query, variables)
        return response['data']['repository']

    def get_repo_traffic(self, owner, repo):
        LOG.info('Requesting GitHub Repo Traffic information for %s/%s', owner, repo)
        gh_headers = {"Authorization": "token " + self.token}
        url_prefix = f'https://api.github.com/repos/{owner}/{repo}/traffic/'
        parts = ['popular/referrers', 'popular/paths', 'views', 'clones']

        traffic = {}
        for part in parts:
            r = requests.get(url_prefix + part, headers=gh_headers)
            traffic[part] = r.json()

        return traffic

    def gh_graphql_query(self, query, variables):
        # A simple function to use requests.post to make the API call. Note the json= section.
        gh_headers = {"Authorization": "token " + self.token}
        request = requests.post('https://api.github.com/graphql',
                                json={'query': query, 'variables': variables},
                                headers=gh_headers)
        if request.status_code == 200:
            return request.json()
        else:
            raise Exception(
                "GH GraphQL query failed to run by returning code of {}. {}".format(request.status_code, query))


