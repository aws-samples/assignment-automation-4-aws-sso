################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

import json
from common.encoder import PythonObjectEncoder


def publish_sqs_task_for_execution(
    controller, accounts, principal_type, principal_id, permission_set_arn, action
):
    payload = []
    results = []
    for idx, account in enumerate(accounts):
        entry = {
            "Id": f"{idx}",
            "MessageBody": json.dumps(
                {
                    "TargetId": account,
                    "PrincipalType": principal_type,
                    "PrincipalId": principal_id,
                    "PermissionSetArn": permission_set_arn,
                    "Action": action,
                },
                indent=2,
                cls=PythonObjectEncoder,
            ),
        }
        controller.clients.logger.info("Uppending entry to array")
        controller.clients.logger.info(entry)
        payload.append(entry)

        ## TODO refactor to look nice. Unfortunately we can send only in batches of 10.
        if (idx + 1) / 10 == 0:
            controller.client.logger.info("Publishing array")
            results.append(
                controller.clients.sqs.send_message_batch(
                    QueueUrl=controller.config.queue_url, Entries=payload
                )
            )
            payload = []
    if payload:
        controller.clients.logger.info("Publishing array")
        results.append(
            controller.clients.sqs.send_message_batch(
                QueueUrl=controller.config.queue_url, Entries=payload
            )
        )
    return results
