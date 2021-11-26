################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


import boto3
import os
import json
import datetime

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from common.error import Error

# Static data

LAMBDA_FUNC_NAME = "Assignment DB handler"
assignment_table_name = os.environ.get("ASSIGNMENTS_TABLE_NAME", "TEST_ASSIGNMENT_TABLE_NAME")
map_key_name = os.getenv("ASSOCIATIONID_KEY_NAME", "mappingId")
map_sortkey_name = os.getenv("ASSOCIATIONID_SORT_KEY_NAME", "mappingValue")
iam_event_bus_arn = os.environ.get("IAM_EVENT_BRIDGE_ARN", "IAM_EVENT_BRIDGE_ARN")

EVENT_SOURCE = "permissionEventSource"
PERMISSION_FOR_OU = "OrganizationalUnit"
PERMISSION_FOR_ACCOUNT = "Account"
PERMISSION_FOR_TAG = "Tag"
PERMISSION_FOR_ROOT = "Root"
PERMISSON_ACTION_ADD = "Add"
PERMISSON_ACTION_REMOVE = "Remove"

session = boto3.Session()
event_bridge_client = session.client("events")

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
ddb_resource = session.resource("dynamodb")
ddb_client = session.client("dynamodb")
ddb_table = ddb_resource.Table(assignment_table_name)
# Mapping Structure:
# "o:{organization_unit}|g:{group_name}|{permission_set_name}"
# "o:Dev-Workbench-DevKit|g:workbench-devkit-developer|WB-DevKit-Developer"
# Sample Mappings:
# a:1234567890|u:testuser|AWSReadOnlyAccess
# o:ou_name|g:Network-Readonly|Network-Readonly
# t:account_tag|u:SomeUser|Readonly
# r:root|g:Sec-Audit|Readonly


def handler(event, context):

    event_source = event.get("source")
    event_detail = event.get("detail")

    if event_source == EVENT_SOURCE:
        permissions = event_detail.get("permissions")
        mapping_records = []
        target_principle = None
        user_principle = None

        for permission_info in permissions:
            action_type = permission_info["ActionType"]

            if permission_info.get("UserName"):
                user = permission_info.get("UserName")
                user_principle = f"u:{user}"
            elif permission_info.get("GroupName"):
                group = permission_info.get("GroupName")
                user_principle = f"g:{group}"
            else:
                raise AttributeError

            permission_type = permission_info["PermissionFor"]

            if permission_type == PERMISSION_FOR_OU:
                organization_unit = permission_info["OrganizationalUnitName"]
                mapping_value_prefix = f"o:{organization_unit}"
                target_principle = organization_unit

            elif permission_type == PERMISSION_FOR_ACCOUNT:
                account_number = permission_info["AccountNumber"]
                mapping_value_prefix = f"a:{account_number}"
                target_principle = account_number

            elif permission_type == PERMISSION_FOR_TAG:
                tag_name = permission_info["TagName"]
                mapping_value_prefix = f"t:{account_number}"
                target_principle = tag_name
            else:
                raise AttributeError

            permission_set_name = permission_info["PermissionSetName"]
            mapping_value = f"{mapping_value_prefix}|{user_principle}|{permission_set_name}"

            if action_type == PERMISSON_ACTION_REMOVE:
                ddb_table.delete_item(
                    Key={
                        map_key_name: str(target_principle),
                        map_sortkey_name: mapping_value,
                    }
                )
            elif action_type == PERMISSON_ACTION_ADD:
                ddb_table.put_item(
                    Item={
                        map_key_name: str(target_principle),
                        map_sortkey_name: mapping_value,
                        "PermissionSetStatus": "Enabled",
                        "PermissionSetName": permission_set_name,
                    }
                )
            else:
                raise AttributeError

    return {
        "statusCode": 200,
        "body": json.dumps("Event was handled properly by Assignment DB Handler."),
    }
