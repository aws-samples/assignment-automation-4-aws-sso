################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


from config import Config_object
from boto3.dynamodb.conditions import Attr
import json


# {
#     'version': '0',
#     'id': 'e6689fa4-5913-75ba-da1e-9e2973c52a88',
#     'detail-type': 'PermissionSetOperation',
#     'source': 'enterprise-aws-sso',
#     'account': '966545059596',
#     'time': '2021-11-22T12:54:13Z',
#     'region': 'us-east-1',
#     'resources': [],
#     'detail':
#         {
#             'Action': 'created',
#             'PermissionSetName':  'SupportUser',
#             'PermissionSetArn':   'arn:aws:sso:::permissionSet/ssoins-72238dcf2af4d70c/ps-578a0ab763537e74'
#         }
# }


def permission_operations_handler(controller: Config_object, event_details: dict):
    print("AWS SSO Event received")

    sso_action = event_details["Action"]
    permission_set_name = event_details["PermissionSetName"]
    permission_set_arn = event_details[
        "PermissionSetArn"
    ]  # Probably will not need this for now, but let's keep it.

    scan_kwargs = {
        "FilterExpression": Attr(controller.config.permission_set_name).eq(permission_set_name),
        "ProjectionExpression": f"{controller.config.map_key_name}, {controller.config.map_sortkey_name}",
    }

    done = False
    start_key = None
    found_items = []
    while not done:
        if start_key:
            scan_kwargs["ExclusiveStartKey"] = start_key
        response = controller.clients.dynamodb_table.scan(**scan_kwargs)
        found_items = found_items + response.get("Items", [])
        start_key = response.get("LastEvaluatedKey", None)
        done = start_key is None

    permission_set_status = "Enabled"
    if sso_action == "deleted":
        permission_set_status = "Disabled"

    for item in found_items:
        controller.clients.logger.debug(item)
        controller.clients.dynamodb_table.put_item(
            Item={
                controller.config.map_key_name: item[controller.config.map_key_name],
                controller.config.map_sortkey_name: item[controller.config.map_sortkey_name],
                controller.config.permission_set_name: permission_set_name,
                controller.config.permission_set_status: permission_set_status,
            }
        )
