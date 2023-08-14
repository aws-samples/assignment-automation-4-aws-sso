################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


import boto3
import os
import json
from aws_assume_role_lib import assume_role
from sso.handler import SsoService
from common.error import Error


class ServerUnavailableException(Exception):
    pass


class UnknownException(Exception):
    pass


# Static data
ACTION_TYPE_CREATE = "CREATE"
ACTION_TYPE_DELETE = "DELETE"
LAMBDA_FUNC_NAME = "Assignment execution handler"


# TODO Set log level as a parameter

session = boto3.Session()


# Proper error handler class
sns_arn = os.getenv(
    "ERROR_TOPIC_NAME", "ERROR_TOPIC_NAME"
)  # Getting the SNS Topic ARN passed in by the environment variables.

error_handler = Error(
    sns_topic=sns_arn,
    session=session,
    lambda_func_name=LAMBDA_FUNC_NAME,
)

logger = error_handler.get_logger()


# Is Identity Center delegated admin?
use_delegated_admin = os.getenv("USE_DELEGATED_ADMIN", False)

# Get SSO Instance
sso_delegated_admin = None

# Get SSO Instance
management_account_id = os.getenv("MANAGEMENT_ACCOUNT_ID", "012345678901")
sso_admin_role_arn = os.getenv(
    "SSO_ADMIN_ROLE_ARN",
    "arn:aws:iam::112223334444:role/assignment-management-role",
)
assumed_admin_role_session = assume_role(session, sso_admin_role_arn)
sso_admin = None


def handler(event, context):
    # TODO make proper call outside handler work with tests
    global sso_admin
    global sso_delegated_admin

    for record in event["Records"]:
        message = record["body"]
        logger.info(message)
        messageDict = json.loads(message)
        principal_type = messageDict["PrincipalType"]
        principal_id = messageDict["PrincipalId"]
        permission_set_arn = messageDict["PermissionSetArn"]
        target_id = messageDict["TargetId"]
        action = messageDict["Action"]

        # For management account and none delegated admin, we use the management account
        if target_id == management_account_id or not use_delegated_admin:
            if sso_admin is None:
                sso_admin = SsoService(assumed_admin_role_session)
            sso = sso_admin
        else:
            if sso_delegated_admin is None:
                sso_delegated_admin = SsoService(session)
            sso = sso_delegated_admin

        if action == ACTION_TYPE_CREATE:
            # Create Account/PermissionSet Assignment
            try:
                response = sso.client.create_account_assignment(
                    InstanceArn=sso.instance_arn,
                    TargetId=target_id,
                    TargetType="AWS_ACCOUNT",
                    PermissionSetArn=permission_set_arn,
                    PrincipalType=principal_type,
                    PrincipalId=principal_id,
                )
                logger.info(response)
                # TODO - According to AccountAssignmentCreationStatus, Status can be 'IN_PROGRESS'|'FAILED'|'SUCCEEDED'
                # If Status is FAILED, What kind of Action is needed?

            except Exception as exception:
                # If Exception occurs, parse Response and write it to Error Topic.
                # Then, raise exception to not delete the message from queue.
                logger.error("Exception: " + str(exception))
                error_handler.publish_error_message(message, str(exception))
                raise (exception)

        elif action == ACTION_TYPE_DELETE:
            # Delete Account/PermissionSet Assignment
            try:
                response = sso.client.delete_account_assignment(
                    InstanceArn=sso.instance_arn,
                    TargetId=target_id,
                    TargetType="AWS_ACCOUNT",
                    PermissionSetArn=permission_set_arn,
                    PrincipalType=principal_type,
                    PrincipalId=principal_id,
                )
                logger.info(response)
            except Exception as exception:
                # If Exception occurs, parse Response and write it to Error Topic.
                # Then, raise exception to not delete the message from queue.
                logger.error("Exception: " + str(exception))
                error_handler.publish_error_message(message, str(exception))
                raise (exception)

        else:
            # Not supported action
            logger.info("Not supported action: " + str(message))
            error_handler.publish_error_message(
                message, "Not supported action.")
            raise AttributeError

    return {
        "statusCode": 200,
        "body": json.dumps("Event was handled properly by Assignment Execution Handler."),
    }
