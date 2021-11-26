################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

from aws_lambda_powertools import Logger
import boto3

logger = Logger()
# TODO Set parametrasable log level


class SsoService:  # pylint: disable=R0904
    """Class used for modeling Organizations"""

    client: boto3.session.Session.client
    instance_arn: str
    identity_store_id: str
    permission_sets: dict

    def __init__(self, boto_session):
        try:
            self.client = boto_session.client("sso-admin")
            self.get_sso_data()
        except Exception as exception:
            # If Exception occurs, parse Response and write it to Error Topic.
            # Then, raise exception to not delete the message from queue.
            logger.error("Exception: " + str(exception))
            raise (exception)

    def get_sso_data(self):
        response = self.client.list_instances()["Instances"][0]
        self.instance_arn = response["InstanceArn"]
        self.identity_store_id = response["IdentityStoreId"]

    def get_permission_sets(self):
        ps_arns = []
        responces = list(
            self.client.get_paginator("list_permission_sets").paginate(
                InstanceArn=self.instance_arn
            )
        )
        for responce in responces:
            ps_arns += responce["PermissionSets"]

        self.permission_sets = {
            ps["PermissionSet"]["Name"]: ps["PermissionSet"]
            for ps_arn in ps_arns
            if (
                ps := self.client.describe_permission_set(
                    InstanceArn=self.instance_arn, PermissionSetArn=ps_arn
                )
            )
            is not None
        }
        return self.permission_sets
