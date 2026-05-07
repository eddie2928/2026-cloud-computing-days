"""2C-2: Lambda triggered by DynamoDB Streams -> CloudWatch custom metrics.
Publishes BlockRate and EventCount metrics per batch.
"""
import os
import boto3

_REGION = os.environ.get("REGION", "us-east-1")
_PROJECT = os.environ.get("PROJECT", "agentbox")
_cw = boto3.client("cloudwatch", region_name=_REGION)


def handler(event, ctx):
    records = event.get("Records", [])
    if not records:
        return

    total = 0
    blocked = 0
    errors = 0

    for record in records:
        if record.get("eventName") not in ("INSERT", "MODIFY"):
            continue
        new_image = record.get("dynamodb", {}).get("NewImage", {})
        verdict = new_image.get("verdict", {}).get("S", "")
        total += 1
        if verdict == "BLOCK":
            blocked += 1
        if new_image.get("error"):
            errors += 1

    if total == 0:
        return

    block_rate = (blocked / total) * 100
    error_rate = (errors / total) * 100

    _cw.put_metric_data(
        Namespace="AgentBox",
        MetricData=[
            {
                "MetricName": "BlockRate",
                "Value": block_rate,
                "Unit": "Percent",
                "Dimensions": [{"Name": "Project", "Value": _PROJECT}],
            },
            {
                "MetricName": "EventCount",
                "Value": total,
                "Unit": "Count",
                "Dimensions": [{"Name": "Project", "Value": _PROJECT}],
            },
            {
                "MetricName": "ErrorRate",
                "Value": error_rate,
                "Unit": "Percent",
                "Dimensions": [{"Name": "Project", "Value": _PROJECT}],
            },
        ],
    )
