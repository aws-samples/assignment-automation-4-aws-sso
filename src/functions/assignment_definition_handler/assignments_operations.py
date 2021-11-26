################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


from typing import List
from processing import process_mapdata
from common.encoder import PythonObjectEncoder
from config import Config_object
import json


def assignments_operations_handler(controller: Config_object, records: list):

    assignment_action: str
    stream_key: str
    aws_principal: str
    idp_principal: str
    permission_set_name: str

    for record in records:
        # TODO switch to parallel processing.
        controller.clients.logger.info(str(record["dynamodb"]))
        controller.clients.logger.debug(
            f"Stream record: {json.dumps(record, indent=2, cls=PythonObjectEncoder)}"
        )
        if "NewImage" in record["dynamodb"]:
            assignment_action = controller.data.ACTION_TYPE_CREATE
            stream_key = "NewImage"
        elif "OldImage" in record["dynamodb"]:
            assignment_action = controller.data.ACTION_TYPE_DELETE
            stream_key = "OldImage"
        else:
            error_msg = f"OldImage nor NewImage key was not found in dynamodb string."
            controller.clients.logger.error(error_msg)
            controller.clients.error_handler.publish_error_message(record, error_msg)
            raise AttributeError

        aws_principal, idp_principal, permission_set_name = record["dynamodb"][stream_key][
            controller.config.map_sortkey_name
        ]["S"].split(controller.config.associationid_concat_char)
        permission_set_state = (
            record["dynamodb"][stream_key]
            .get(controller.config.permission_set_status)
            .get("S", "Enabled")
        )
        if permission_set_state == "Enabled":
            process_mapdata(
                controller,
                aws_principal,
                idp_principal,
                permission_set_name,
                assignment_action,
                record,
            )
        else:
            controller.clients.logger.info(
                f"Permission set {permission_set_name} is disabled. Removing permissions from AWS SSO"
            )
            process_mapdata(
                controller,
                aws_principal,
                idp_principal,
                permission_set_name,
                controller.data.ACTION_TYPE_DELETE,
                record,
            )
