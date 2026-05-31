#!/usr/bin/env bash
# Install CloudWatch agent on Ubuntu EC2 to ship syslog (OOM killer) and memory metrics.
# Run once on the instance after: terraform apply
set -euo pipefail

REGION="${AWS_REGION:-ap-south-1}"
LOG_GROUP="${CLOUDWATCH_SYSTEM_LOG_GROUP:-}"

if [[ -z "$LOG_GROUP" ]]; then
  echo "Set CLOUDWATCH_SYSTEM_LOG_GROUP (terraform output cloudwatch_system_log_group)" >&2
  exit 1
fi

INSTANCE_ID="$(curl -s http://169.254.169.254/latest/meta-data/instance-id)"
ARCH="$(dpkg --print-architecture)"

if ! command -v amazon-cloudwatch-agent-ctl &>/dev/null; then
  wget -q "https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/${ARCH}/latest/amazon-cloudwatch-agent.deb" \
    -O /tmp/amazon-cloudwatch-agent.deb
  sudo dpkg -i /tmp/amazon-cloudwatch-agent.deb
fi

sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json >/dev/null <<EOF
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "${LOG_GROUP}",
            "log_stream_name": "${INSTANCE_ID}/syslog",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/kern.log",
            "log_group_name": "${LOG_GROUP}",
            "log_stream_name": "${INSTANCE_ID}/kern",
            "timezone": "UTC"
          }
        ]
      }
    }
  },
  "metrics": {
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent", "mem_available", "mem_used"]
      }
    },
    "append_dimensions": {
      "InstanceId": "${INSTANCE_ID}"
    }
  }
}
EOF

sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s

echo "CloudWatch agent running. Syslog/OOM lines → ${LOG_GROUP}"
