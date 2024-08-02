################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

import json
from processing import process_mapdata, PrincipalNotFound
from config import Config_object


# {
#  "AccountOperations":
#     {
#       "Action": "tagged|created|moved",
#       "TagKey": "",
#       "TagValue": "",
#       "AccountId": "",
#       "AccountOuName": "",
#       "AccountOldOuName": "",
#     }
# }


def account_operations_handler(controller: Config_object, payload: dict):
    controller.clients.logger.info("Received event from Service Handler.")
    action: str = payload.get("Action")
    account_id: str = payload.get("AccountId")
    tag_key: str = payload.get("TagKey")
    tag_value: str = payload.get("TagValue")
    parent_ou_name: str = payload.get("AccountOuName")
    parent_old_ou_name: str = payload.get("AccountOldOuName")

    # Tag deletion is now handled as an untagresource api call when done from the web console. Can now be implemented.
    # if action == "tagged":
    #     if tag_key is not None:
    #         controller.clients.logger.info(f"Org action detected. Account is tagged")
    #         query_dynamo_table(
    #            controller, f"{tag_key}={tag_value}", account_id, controller.data.ACTION_TYPE_CREATE
    #         )
    if action == "created":
        controller.clients.logger.info(f"Organizatins action detected. Account is created")
        query_dynamo_table(controller, "root", account_id, controller.data.ACTION_TYPE_CREATE)
    if action == "moved":
        controller.clients.logger.info(f"Organizations action detected. Account is moved")
        query_dynamo_table(
            controller,
            (
                "root"
                if parent_old_ou_name.startswith("r-")
                else controller.clients.org.describe_ou_name(parent_old_ou_name)
            ),
            account_id,
            controller.data.ACTION_TYPE_DELETE,
        )
        if not parent_ou_name.startswith("r-"):
            query_dynamo_table(
                controller,
                controller.clients.org.describe_ou_name(parent_ou_name),
                account_id,
                controller.data.ACTION_TYPE_CREATE,
            )
    return {
        "statusCode": 200,
        "body": json.dumps("Received Organizations Event has been successfully processed."),
    }


def query_dynamo_table(controller, query_key, account_id, assignment_action):
    key_condition_expression_value = f"{controller.config.map_key_name} = :queryValue"
    result = controller.clients.dynamodb.query(
        TableName=controller.config.table_name,
        KeyConditionExpression=key_condition_expression_value,
        ExpressionAttributeValues={":queryValue": {"S": query_key}},
    )
    controller.clients.logger.info(f"search results :{str(result)}")

    if result.get("Count") > 0:
        for item in result["Items"]:
            aws_principal, idp_principal, permission_set_name = item[
                controller.config.map_sortkey_name
            ]["S"].split(controller.config.associationid_concat_char)
            try:
                process_mapdata(
                    controller,
                    f"a:{account_id}",
                    idp_principal,
                    permission_set_name,
                    assignment_action,
                    item,
                )
            except PrincipalNotFound:
                controller.clients.logger.info(
                    f"Principal {idp_principal} missing, moving on to next record from DynamoDB"
                )
