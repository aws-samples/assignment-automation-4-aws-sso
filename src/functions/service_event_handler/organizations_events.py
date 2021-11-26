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


def process_organizations_event(event: dict) -> Tuple[str, dict]:
    operation_name = "AccountOperation"
    operation_event = {}
    try:
        event_name: str = event["detail"]["eventName"]
        if event_name == "CreateAccountResult":
            operation_event["Action"] = "created"
            account_status: dict = event["detail"]["serviceEventDetails"]
            account_state: str = account_status["state"]
            if not account_state == "SUCCEEDED":
                return operation_name, {}
            operation_event["AccountId"] = account_status["account"]["accountId"]
        elif event_name == "MoveAccount":
            operation_event["Action"] = "moved"
            request_parameters: dict = event["detail"].get("requestParameters")
            operation_event["AccountId"] = request_parameters["accountId"]
            operation_event["AccountOuName"] = request_parameters["destinationParentId"]
            operation_event["AccountOldOuName"] = request_parameters["sourceParentId"]
        else:
            logger.error(f"Action for Lifecycle Event {event_name} not defined")
            raise OrganizationsEventError("Action for Lifecycle Event not defined")
        return operation_name, operation_event

    except KeyError as e:
        logger.error(e)
        logger.error(json.dumps(event))
        raise OrganizationsEventError(
            "Failed to load information from Control Tower Lifecycle Event"
        ) from e


class OrganizationsEventError(Exception):
    """Error while processing AWS Control Tower Lifecycle Event"""

    pass
