################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


import backoff
import boto3
import os
import json
from aws_assume_role_lib import assume_role
from botocore import exceptions
from common.error import Error
from sso.handler import SsoService


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
use_delegated_admin = None

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
    global use_delegated_admin

    # check if delegated admin is enabled
    if use_delegated_admin is None:
        try:
            org_client = assumed_admin_role_session.client(
                "organizations"
            )
            response = org_client.list_delegated_administrators(
                ServicePrincipal="sso.amazonaws.com",
            )
            logger.info(response)
            delegated_admins = response.get("DelegatedAdministrators", [])
            if delegated_admins:
                for admin in delegated_admins:
                    if admin.get("Status") == "ACTIVE":
                        use_delegated_admin = True
            else:
                use_delegated_admin = False
        except exceptions.ClientError as exception:
            logger.error("Exception: " + str(exception))
            error_handler.publish_error_message(
                "Failed to retrieve 'sso.amazonaws.com' delegated administrators.", str(exception)
            )
            raise (exception)

    logger.info("use_delegated_admin is set to " + str(use_delegated_admin))

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

            @backoff.on_exception(
                backoff.expo,
                (
                    sso.client.exceptions.ConflictException,
                    sso.client.exceptions.ThrottlingException,
                ),
                max_tries=10,
            )
            def create_account_assignment(
                message, principal_type, principal_id, permission_set_arn, target_id, sso
            ):
                response = sso.client.create_account_assignment(
                    InstanceArn=sso.instance_arn,
                    TargetId=target_id,
                    TargetType="AWS_ACCOUNT",
                    PermissionSetArn=permission_set_arn,
                    PrincipalType=principal_type,
                    PrincipalId=principal_id,
                )
                logger.info(response)

            # Create Account/PermissionSet Assignment
            try:
                create_account_assignment(
                    message, principal_type, principal_id, permission_set_arn, target_id, sso
                )
            except Exception as exception:
                # If Exception occurs, parse Response and write it to Error Topic.
                # Then, raise exception to not delete the message from queue.
                logger.error("Exception: " + str(exception))
                error_handler.publish_error_message(message, str(exception))
                raise (exception)

        elif action == ACTION_TYPE_DELETE:

            @backoff.on_exception(
                backoff.expo,
                (
                    sso.client.exceptions.ConflictException,
                    sso.client.exceptions.ThrottlingException,
                ),
                max_tries=10,
            )
            def delete_account_assignment(
                principal_type, principal_id, permission_set_arn, target_id, sso
            ):
                response = sso.client.delete_account_assignment(
                    InstanceArn=sso.instance_arn,
                    TargetId=target_id,
                    TargetType="AWS_ACCOUNT",
                    PermissionSetArn=permission_set_arn,
                    PrincipalType=principal_type,
                    PrincipalId=principal_id,
                )
                logger.info(response)

            # Delete Account/PermissionSet Assignment
            try:
                delete_account_assignment(
                    principal_type, principal_id, permission_set_arn, target_id, sso
                )
            except Exception as exception:
                # If Exception occurs, parse Response and write it to Error Topic.
                # Then, raise exception to not delete the message from queue.
                logger.error("Exception: " + str(exception))
                error_handler.publish_error_message(message, str(exception))
                raise (exception)

        else:
            # Not supported action
            logger.info("Not supported action: " + str(message))
            error_handler.publish_error_message(message, "Not supported action.")
            raise AttributeError

    return {
        "statusCode": 200,
        "body": json.dumps("Event was handled properly by Assignment Execution Handler."),
    }
