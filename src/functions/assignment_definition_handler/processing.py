################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


from sqs import publish_sqs_task_for_execution
from config import Config_object


def process_mapdata(
    controller: Config_object,
    aws_principal: str,
    idp_principal: str,
    permission_set_name: str,
    assignment_action: str,
    record: str,
):
    aws_principal_type: str
    aws_principal_name: str
    aws_principal_type, aws_principal_name = aws_principal.split(":")

    idp_principal_type: str
    idp_principal_name: str
    idp_principal_type, idp_principal_name = idp_principal.split(":")

    if permission_set_name in controller.data.permission_sets:
        permission_set: str = controller.data.permission_sets[permission_set_name]
        controller.clients.logger.info(
            f"PS {permission_set_name} identified as: {permission_set['PermissionSetArn']}"
        )
    else:
        error_msg = f"Permission Set {permission_set_name} was not found."
        controller.clients.logger.error(error_msg)
        controller.clients.error_handler.publish_error_message(record, error_msg)
        pass

    accounts = None
    if idp_principal_type.lower() == "g":
        idp_principal: dict = controller.clients.identity_store.list_groups(
            IdentityStoreId=controller.clients.sso.identity_store_id,
            Filters=[
                {
                    "AttributePath": "DisplayName",
                    "AttributeValue": idp_principal_name,
                }
            ],
        )["Groups"][0]
        controller.clients.logger.info(
            f"Group {idp_principal['DisplayName']} identified as: {idp_principal['GroupId']}."
        )
        idp_principal["Type"] = controller.data.GROUP_PRINCIPAL_TYPE
        idp_principal["Id"] = idp_principal["GroupId"]
    elif idp_principal_type.lower() == "u":
        idp_principal: dict = controller.clients.identity_store.list_users(
            IdentityStoreId=controller.clients.sso.identity_store_id,
            Filters=[{"AttributePath": "UserName", "AttributeValue": idp_principal_name}],
        )["Users"][0]
        controller.clients.logger.info(
            f"User {idp_principal['UserName']} identified as: {idp_principal['UserId']}."
        )
        idp_principal["Type"] = controller.data.USER_PRINCIPAL_TYPE
        idp_principal["Id"] = idp_principal["UserId"]
    else:
        error_msg = f'principal type {idp_principal_type} is not supported. Needs to be either a user ("u") or group ("g")'
        controller.clients.logger.error(error_msg)
        controller.clients.error_handler.publish_error_message(record, error_msg)
        pass
    if aws_principal_type.lower() == "r":
        # Apply to all accounts that exist under root
        controller.clients.logger.info(
            "Root request received. Changes marked for all accounts in this Organization"
        )
        accounts = controller.clients.org.get_accounts_ids()
    elif aws_principal_type.lower() == "o":
        # Get accounts for OU
        controller.clients.logger.info(
            f"OU request received. Changes marked for accounts in {aws_principal_name} OU"
        )
        accounts = controller.clients.org.get_active_accounts_for_path(f"/{aws_principal_name}")
        controller.clients.logger.info(accounts)
    elif aws_principal_type.lower() == "a":
        # Validate account and proceed with it.
        account = controller.clients.org.describe_account(aws_principal_name)
        if account["Account"]["Status"] == "ACTIVE":
            controller.clients.logger.info(
                f"Account {aws_principal_name} is an active account and will be processed"
            )
            accounts = [aws_principal_name]
        else:
            error_msg = f"AWS Account {aws_principal_name} was not found or is not active"
            controller.clients.logger.error(error_msg)
            controller.clients.error_handler.publish_error_message(record, error_msg)
    elif aws_principal_type.lower() == "t":
        # Get accounts with tags.
        controller.clients.logger.info(
            f"Tag request received. Changes marked for accounts with {aws_principal_name} tag"
        )
        tag_key, tag_value = aws_principal_name.split("=")
        accounts = controller.clients.org.get_account_ids_for_tags({tag_key: tag_value})
    else:
        error_msg = f'AWS principal type {aws_principal_type} is not supported. Needs to be one of following: root ("r"), organization unit ("o"), account ("a") or tag ("r")'
        controller.clients.logger.error(error_msg)
        controller.clients.error_handler.publish_error_message(record, error_msg)
        pass
    if accounts:
        publish_sqs_task_for_execution(
            controller,
            accounts=accounts,
            principal_type=idp_principal["Type"],
            principal_id=idp_principal["Id"],
            permission_set_arn=permission_set["PermissionSetArn"],
            action=assignment_action,
        )
    else:
        error_msg = f"Root AWS Organization does not have active accounts"
        controller.clients.logger.error(error_msg)
        controller.clients.error_handler.publish_error_message(record, error_msg)
