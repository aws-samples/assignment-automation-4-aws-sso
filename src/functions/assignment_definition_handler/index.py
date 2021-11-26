################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

import json

from account_operations import account_operations_handler
from assignments_operations import assignments_operations_handler
from permissionset_operations import permission_operations_handler
from config import load_config


controller = None

## Event payload from Service Event handler: 
# {
#   "Source": "enterprise-aws-sso",
#   "DetailType": "AccountOperations",
#   "Detail": 
#     {
#       "Action": "tagged|created|moved",
#       "TagKey": "",
#       "TagValue": "",
#       "AccountId": "",
#       "AccountOuName": "",
#       "AccountOldOuName": "If present if not have to look for a solutoin",
#     }
# }
# {
#     "PermissionSetOperations": 
#     {
#         "Action": "created|delete",
#         "PermissionSetName": "",
#     }
# }

# This will be the control lambda! 

# @logger.inject_lambda_context
def handler(event: dict, context):
    global controller

    if controller is None:
        controller = load_config()

    if event_source := event.get("source"):
        if event_source == "enterprise-aws-sso": 
                detail_type = event.get("detail-type")
                if  detail_type == "AccountOperation":
                        account_operations_handler(controller, event.get("detail"))
                if detail_type == "PermissionSetOperation":
                        permission_operations_handler(controller, event.get("detail"))
    elif records := event.get("Records"):
            assignments_operations_handler(controller, records)

    return {
        "statusCode": 200,
        "body": json.dumps(f'Event processed'),
    }
