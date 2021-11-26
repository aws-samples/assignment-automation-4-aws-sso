################################################################################
# © 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer
# Agreement available at http://aws.amazon.com/agreement or other written
# agreement between Customer and either Amazon Web Services, Inc. or Amazon
# Web Services EMEA SARL or both.
################################################################################
import json
from aws_lambda_powertools import Logger
from typing import Tuple

logger = Logger(child=True)


def process_awssso_event(event: dict) -> Tuple[str, dict]:
    operation_name = "PermissionSetOperation"
    operation_event = {}
    try:
        event_name: str = event["detail"]["eventName"]
        request_params: dict = event["detail"]["requestParameters"]
        if event_name == "CreatePermissionSet":
            operation_event["Action"] = "created"
            response_params: dict = event["detail"]["responseElements"]["permissionSet"]
            operation_event["PermissionSetName"] = request_params["name"]
            operation_event["PermissionSetArn"] = response_params["permissionSetArn"]
        elif event_name == "DeletePermissionSet":
            operation_event["Action"] = "deleted"
            operation_event["PermissionSetArn"] = request_params["permissionSetArn"]
        else:
            logger.error(f"Action for AWS SSO Event {event_name} not defined")
            raise AWSSSOEventError("Action for Lifecycle Event not defined")
        return operation_name, operation_event

    except KeyError as e:
        logger.error(e)
        logger.error(json.dumps(event))
        raise AWSSSOEventError(
            "Failed to load information from Control Tower Lifecycle Event"
        ) from e


class AWSSSOEventError(Exception):
    """Error while processing AWS SSO Event"""

    pass
