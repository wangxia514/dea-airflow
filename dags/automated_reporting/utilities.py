"""
Common code needed for reporting dags
"""

NCI_TUNNEL_CMDS = [
    "mkdir -p ~/.ssh",
    "cat /var/secrets/lpgs/PORT_FORWARDER_KEY > ~/.ssh/identity_file.pem",
    "chmod 0400 ~/.ssh/identity_file.pem",
    "echo Establishing NCI tunnel",
    "ssh -o StrictHostKeyChecking=no -f -N -i ~/.ssh/identity_file.pem -L 54320:$ODC_DB_HOST:$ODC_DB_PORT $NCI_TUNNEL_USER@$NCI_TUNNEL_HOST",
    "echo NCI tunnel established",
]
