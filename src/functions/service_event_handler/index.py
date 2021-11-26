################################################################################
# © 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer
# Agreement available at http://aws.amazon.com/agreement or other written
# agreement between Customer and either Amazon Web Services, Inc. or Amazon
# Web Services EMEA SARL or both.
################################################################################
import datetime
import json
import os

import boto3
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source
from common.error import Error
from common.encoder import PythonObjectEncoder
from organizations_events import process_organizations_event
from awssso_events import process_awssso_event

LAMBDA_FUNCTION_NAME = "service_event_handler"

session = boto3.Session()

sns_arn = os.getenv("ERROR_TOPIC_NAME", "ERROR_TOPIC_NAME")
iam_event_bus_arn = os.environ.get("IAM_EVENT_BRIDGE_ARN", "IAM_EVENT_BRIDGE_ARN")

error_handler = Error(
    sns_topic=sns_arn,
    session=session,
    lambda_func_name=LAMBDA_FUNCTION_NAME,
)
logger = error_handler.get_logger()

event_bridge_client = session.client("events")

event_processors = {
    "aws.organizations": process_organizations_event,
    "aws.sso": process_awssso_event,
}


def send_event(event_type: str, payload: dict) -> None:
    event_payload = [
        {
            "Time": datetime.datetime.now().isoformat(),
            "Source": "enterprise-aws-sso",
            "Resources": [],
            "DetailType": event_type,
            "Detail": json.dumps(payload, cls=PythonObjectEncoder),
            "EventBusName": iam_event_bus_arn,
        },
    ]
    event_bridge_client.put_events(Entries=event_payload)


@event_source(data_class=EventBridgeEvent)
def handler(event: EventBridgeEvent, context):

    logger.debug(event.raw_event)
    if event.source not in event_processors.keys():
        logger.error("Event source is not supported")
        raise UnsupportedEvent()

    event_type, processed_service_event = event_processors[event.source](event.raw_event)

    if processed_service_event:
        send_event(event_type, processed_service_event)


class UnsupportedEvent(Exception):
    """Event source is not supported"""

    pass
