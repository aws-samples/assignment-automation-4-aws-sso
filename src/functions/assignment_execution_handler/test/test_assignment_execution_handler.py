################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

import botocore
import datetime
import unittest

from aws_lambda_powertools import Logger
from botocore.stub import Stubber

from .. import index
from sso.test.test_sso_handler import TestSsoLayer

from assignment_execution_handler.test.payloads import (
    event_input_data_create,
    event_input_data_delete,
)


logger = Logger()

"""
Assignment execution testing testing class
"""


class TestApp(unittest.TestCase):  # pylint: disable=R0904,C0116
    # Setting up clients
    sso_admin = botocore.session.get_session().create_client("sso-admin")
    sso_admin_stubber = Stubber(sso_admin)

    # Loading paramteres to the SSO Layer mock
    sso_layer_mock = TestSsoLayer()
    sso = sso_layer_mock.test_0_sso_list_instances()

    # Adding mocked SSO layer to lambda function
    index.sso = sso
    index.sso.client = sso_admin

    """
    Assignment execution create event test
    """

    def test_0_handler_assignment_execution_handler_create_success(self):
        self.sso_admin_stubber.add_response(
            "create_account_assignment",
            service_response={
                "AccountAssignmentCreationStatus": {
                    "CreatedDate": datetime.datetime.now().isoformat(),
                    "FailureReason": "string",
                    "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb",
                    "PrincipalId": "string",
                    "PrincipalType": "string",
                    "RequestId": "string",
                    "Status": "string",
                    "TargetId": "string",
                    "TargetType": "string",
                }
            },
            expected_params={
                "InstanceArn": "arn:aws:iam::112223334444:ssoinstance",
                "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb",
                "PrincipalId": "string",
                "PrincipalType": "string",
                "TargetId": "string",
                "TargetType": "AWS_ACCOUNT",
            },
        )
        self.sso_admin_stubber.activate()

        res = index.handler(event_input_data_create, {})
        assert res is not None
        statusCode = res["statusCode"]
        assert statusCode == 200

    """
    Assignment execution delete event test
    """

    def test_1_handler_assignment_execution_handler_delete_success(self):
        index.sso.client = self.sso_admin

        self.sso_admin_stubber.add_response(
            "delete_account_assignment",
            service_response={
                "AccountAssignmentDeletionStatus": {
                    "CreatedDate": datetime.datetime.now().isoformat(),
                    "FailureReason": "string",
                    "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb",
                    "PrincipalId": "string",
                    "PrincipalType": "string",
                    "RequestId": "string",
                    "Status": "string",
                    "TargetId": "string",
                    "TargetType": "string",
                }
            },
            expected_params={
                "InstanceArn": "arn:aws:iam::112223334444:ssoinstance",
                "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb",
                "PrincipalId": "string",
                "PrincipalType": "string",
                "TargetId": "string",
                "TargetType": "AWS_ACCOUNT",
            },
        )

        self.sso_admin_stubber.activate()
        res = index.handler(event_input_data_delete, {})
        assert res is not None
