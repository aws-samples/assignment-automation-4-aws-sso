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
#       "Action": "tagged|untagged|created|moved",
#       "AccountTags": [ # for tagged
#           {
#               "key": "key1",
#               "value": "value1",
#           }
#        ]
#       "AccountTagKeys": [ # for untagged
#           "key1"
#        ]
#       "AccountId": "",
#       "AccountOuName": "", # for created or moved
#       "AccountOldOuName": "", # for created or moved
#     }
# }


def account_operations_handler(controller: Config_object, payload: dict):
    controller.clients.logger.info("Received event from Service Handler.")
    action: str = payload.get("Action")
    account_id: str = payload.get("AccountId")
    parent_ou_name: str = payload.get("AccountOuName")
    parent_old_ou_name: str = payload.get("AccountOldOuName")
    tags: list = payload.get("AccountTags", [])
    tag_keys: list = payload.get("AccountTagKeys", [])

    match action:
        case "tagged":
            controller.clients.logger.info(f"Org action detected. Account is tagged")
            if not tags:
                controller.clients.logger.info(
                    f"Organizations action detected. Account is tagged, but no tags found"
                )
                return {
                    "statusCode": 200,
                    "body": json.dumps("No tags found"),
                }
            for tag in tags:
                tag_key = tag.get("key")
                tag_value = tag.get("value")
                result = query_dynamo_table(controller, f"{tag_key}")
                if result.get("Count") == 0:
                    controller.clients.logger.info(f"Tag key {tag_key} not found in DynamoDB")
                    continue
                for item in result["Items"]:
                    aws_principal, idp_principal, permission_set_name = item[
                        controller.config.map_sortkey_name
                    ]["S"].split(controller.config.associationid_concat_char)
                    record_tag_key, record_tag_value = aws_principal.split("=")

                    if record_tag_value == tag_value:
                        controller.clients.logger.info(f"Tag value {tag_value} is a match.")
                        process_records(
                            controller,
                            account_id,
                            idp_principal,
                            permission_set_name,
                            controller.data.ACTION_TYPE_CREATE,
                        )
                    else:
                        controller.clients.logger.info(
                            f"Tag value {tag_value} is not a match. Deleting potential permissions."
                        )
                        process_records(
                            controller,
                            account_id,
                            idp_principal,
                            permission_set_name,
                            controller.data.ACTION_TYPE_DELETE,
                        )

        case "untagged":
            controller.clients.logger.info(f"Org action detected. Account is untagged")
            controller.clients.logger.debug(f"Tag keys: {tag_keys}")
            if not tag_keys:
                controller.clients.logger.info(
                    f"Organizations action detected. Account is untagged, but no tag keys found"
                )
                return {
                    "statusCode": 200,
                    "body": json.dumps("No tag keys found"),
                }
            for tag_key in tag_keys:
                result = query_dynamo_table(
                    controller,
                    f"{tag_key}",
                )
                if result.get("Count") == 0:
                    controller.clients.logger.info(f"Tag key {tag_key} not found in DynamoDB")
                    continue
                for item in result["Items"]:
                    aws_principal, idp_principal, permission_set_name = item[
                        controller.config.map_sortkey_name
                    ]["S"].split(controller.config.associationid_concat_char)

                    process_records(
                        controller,
                        account_id,
                        idp_principal,
                        permission_set_name,
                        controller.data.ACTION_TYPE_DELETE,
                    )
        case "created":
            controller.clients.logger.info(f"Organizations action detected. Account is created")
            result = query_dynamo_table(controller, "root")
            for item in result["Items"]:
                aws_principal, idp_principal, permission_set_name = item[
                    controller.config.map_sortkey_name
                ]["S"].split(controller.config.associationid_concat_char)

                process_records(
                    controller,
                    account_id,
                    idp_principal,
                    permission_set_name,
                    controller.data.ACTION_TYPE_CREATE,
                )

        case "moved":
            controller.clients.logger.info(f"Organizations action detected. Account is moved")

            # When moving accounts, root scoped permissions shouldn't be removed
            if not parent_old_ou_name.startswith("r-"):
                delete_result = query_dynamo_table(
                    controller,
                    (
                        "root"
                        if parent_old_ou_name.startswith("r-")
                        else controller.clients.org.describe_ou_name(parent_old_ou_name)
                    ),
                )

                for item in delete_result["Items"]:
                    aws_principal, idp_principal, permission_set_name = item[
                        controller.config.map_sortkey_name
                    ]["S"].split(controller.config.associationid_concat_char)

                    process_records(
                        controller,
                        account_id,
                        idp_principal,
                        permission_set_name,
                        controller.data.ACTION_TYPE_DELETE,
                    )

            # When moving accounts, root scoped permissions shouldn't need to be recreated
            if not parent_ou_name.startswith("r-"):
                create_result = query_dynamo_table(
                    controller, controller.clients.org.describe_ou_name(parent_ou_name)
                )
                for item in create_result["Items"]:
                    aws_principal, idp_principal, permission_set_name = item[
                        controller.config.map_sortkey_name
                    ]["S"].split(controller.config.associationid_concat_char)

                    process_records(
                        controller,
                        account_id,
                        idp_principal,
                        permission_set_name,
                        controller.data.ACTION_TYPE_CREATE,
                    )

    return {
        "statusCode": 200,
        "body": json.dumps("Received Organizations Event has been successfully processed."),
    }


def query_dynamo_table(controller, query_key) -> dict:
    key_condition_expression_value = f"{controller.config.map_key_name} = :queryValue"
    result: dict = controller.clients.dynamodb.query(
        TableName=controller.config.table_name,
        KeyConditionExpression=key_condition_expression_value,
        ExpressionAttributeValues={":queryValue": {"S": query_key}},
    )
    controller.clients.logger.info(f"search results :{str(result)}")
    return result


def process_records(
    controller, account_id: str, idp_principal: str, permission_set_name: str, assignment_action
):
    controller.clients.logger.info(
        f"Processing ({assignment_action}) access to {account_id} for {idp_principal} using {permission_set_name}"
    )
    try:
        process_mapdata(
            controller,
            f"a:{account_id}",
            idp_principal,
            permission_set_name,
            assignment_action,
        )
    except PrincipalNotFound:
        controller.clients.logger.info(f"Principal {idp_principal} missing in Identity Center")
