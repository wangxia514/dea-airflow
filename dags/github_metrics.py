"""
# Record available Metrics from DEA and ODC GitHub Repositories

GitHub only stores these metrics for 14 days, and most of them
are much more interesting over the longer term.

They are written into a PostgreSQL table as JSON-B for later analysis.

For inspiration on a potentially nicer implementation see https://github.com/vparekh94/test_ssh_tunnel/tree/master/

## Expects
Connections:
- `lpgs_pg` for connecting to remote PostgreSQL server
- `lpgs_gadi` for setting up SSH tunnel to PostgreSQL
- `github_metrics_token` containing a GitHub token with public repo permissions

"""
import logging

from datetime import datetime
from psycopg2.extras import Json
import psycopg2
import requests
from airflow import DAG
from airflow import secrets
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.operators.python_operator import PythonOperator

LOG = logging.getLogger(__name__)

TRACKED_REPOS = [
    ("opendatacube", "datacube-core"),
    ("opendatacube", "datacube-stats"),
    ("opendatacube", "datacube-explorer"),
    ("opendatacube", "datacube-ows"),
    ("opendatacube", "dea-proto"),
    ("GeoscienceAustralia", "digitalearthau"),
    ("GeoscienceAustralia", "wofs"),
    ("GeoscienceAustralia", "fc"),
    ("GeoscienceAustralia", "dea-cogger"),
]


def log(text):
    print(text)


def _record_statistics(ts, postgres_conn_id, ssh_conn_id, **context):
    # Can't use PostgresHook because our TCP port is likely to be dynamic
    # because we are connecting through an SSH Tunnel
    (pg_secret,) = secrets.get_connections(postgres_conn_id)
    (gh_token,) = secrets.get_connections("github_metrics_token")

    ssh_conn = SSHHook(ssh_conn_id=ssh_conn_id)
    tunnel = ssh_conn.get_tunnel(remote_port=pg_secret.port, remote_host=pg_secret.host)

    tunnel.start()
    with tunnel:
        log(f"Connected SSH Tunnel: {tunnel}")
        # Airflow conflates dbname and schema, even though they are very different in PG
        constr = (
            f"host=localhost user={pg_secret.login} dbname={pg_secret.schema} "
            f"port={tunnel.local_bind_port} password={pg_secret.password}"
        )
        # It's important to wrap this connection in a try/finally block, otherwise
        # we can cause a deadlock with the SSHTunnel
        conn = psycopg2.connect(constr)
        try:
            log(f"Connected to Postgres: {conn}")

            cur = conn.cursor()
            # ensure_pg_table(cur)

            stats_retriever = GitHubStatsRetriever(gh_token.password)

            for owner, repo in TRACKED_REPOS:
                log(f"Recording repo stats for {owner}/{repo}")
                stats = stats_retriever.get_repo_stats(owner, repo)
                log(stats)

                save_record_to_pg(cur, ts, f"{owner}/{repo}", stats)

            conn.commit()
            log("Transaction committed")
            cur.close()
        finally:
            conn.close()


def ensure_pg_table(cur):
    cur.execute("SELECT * from agdc.dataset_type LIMIT 1;")
    log(cur.fetchone())
    cur.execute(
        """CREATE TABLE IF NOT EXISTS metrics.gh_metrics_raw (
                   timestamp timestamp,
                   repo text,
                   data jsonb,
                   PRIMARY KEY (timestamp, repo));"""
    )


def save_record_to_pg(cur, timestamp, repo, record):
    cur.execute(
        """
        INSERT INTO metrics.gh_metrics_raw (timestamp, repo, data) VALUES(%s, %s, %s)
        ON CONFLICT DO NOTHING;
    """,
        [timestamp, repo, Json(record)],
    )


default_args = {"owner": "dayers", "start_date": datetime(2020, 6, 15)}

dag = DAG(
    dag_id="github_metrics",
    catchup=False,
    default_args=default_args,
    schedule_interval="@daily",
    default_view="graph",
    tags=["nci"],
    doc_md=__doc__,
)


with dag:
    record_statistics = PythonOperator(
        task_id="record_statistics",
        python_callable=_record_statistics,
        op_kwargs=dict(postgres_conn_id="lpgs_pg", ssh_conn_id="lpgs_gadi"),
        provide_context=True,
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

        stats["traffic"] = self.get_repo_traffic(owner, repo)

        return stats

    def get_graphql_stats(self, owner, repo):
        # language=GraphQL
        query = """
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
        """
        variables = {"owner": owner, "repo": repo}

        response = self.gh_graphql_query(query, variables)
        if "data" in response:
            return response["data"]["repository"]
        else:
            raise Exception("Invalid response", response)

    def get_repo_traffic(self, owner, repo):
        LOG.info("Requesting GitHub Repo Traffic information for %s/%s", owner, repo)
        gh_headers = {"Authorization": "token " + self.token}
        url_prefix = f"https://api.github.com/repos/{owner}/{repo}/traffic/"
        parts = ["popular/referrers", "popular/paths", "views", "clones"]

        traffic = {}
        for part in parts:
            r = requests.get(url_prefix + part, headers=gh_headers)
            traffic[part] = r.json()

        return traffic

    def gh_graphql_query(self, query, variables):
        # A simple function to use requests.post to make the API call. Note the json= section.
        gh_headers = {"Authorization": "token " + self.token}
        request = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=gh_headers,
        )
        if request.status_code == 200:
            return request.json()
        else:
            raise Exception(
                "GH GraphQL query failed to run by returning code of {}. {}".format(
                    request.status_code, query
                )
            )
