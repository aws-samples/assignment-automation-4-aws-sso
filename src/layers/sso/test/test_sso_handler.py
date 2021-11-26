################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


import datetime
import unittest
import botocore


from unittest.mock import Mock, patch
from botocore.stub import Stubber, ANY
from aws_lambda_powertools import Logger

from .. import handler

logger = Logger()

"""
SSO Layer testing class
"""


class TestSsoLayer(unittest.TestCase):

    sso_client = botocore.session.get_session().create_client("sso-admin")
    sso_client_stubber = Stubber(sso_client)

    """
    This method is used to override the actuall init function 
    of a class in order to receive objects with all class methods.
    Such appraoch allows to redefine boto3 clients with 
    mocks and test/use this class as a mock
    """

    def empty_class_init(self, boto_session):
        pass

    """
    SSO Layer testing function
    """

    def test_0_sso_list_instances(self):
        self.sso_client_stubber.add_response(
            "list_instances",
            {
                "Instances": [
                    {
                        "InstanceArn": "arn:aws:iam::112223334444:ssoinstance",
                        "IdentityStoreId": "d-2b57a3f2cb",
                    },
                ],
                "NextToken": "string",
            },
            {},
        )

        self.sso_client_stubber.add_response(
            "list_permission_sets",
            {
                "PermissionSets": [
                    "arn:aws:sso:::permissionSet/ssoins-72238dcf2af4d70c/ps-ee56096dded3dd82",
                    "arn:aws:sso:::permissionSet/ssoins-72238dcf2af4d70c/ps-1cf71c9d3ac397d2",
                    "arn:aws:sso:::permissionSet/ssoins-72238dcf2af4d70c/ps-63fe84230b679882",
                ],
                "ResponseMetadata": {
                    "RequestId": "8343a836-2eb4-4c5c-9556-0aaad4acdc27",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                        "date": "Thu, 22 Jul 2021 15:49:35 GMT",
                        "content-type": "application/x-amz-json-1.1",
                        "content-length": "464",
                        "connection": "keep-alive",
                        "x-amzn-requestid": "8343a836-2eb4-4c5c-9556-0aaad4acdc27",
                    },
                    "RetryAttempts": 0,
                },
            },
            {"InstanceArn": "arn:aws:iam::112223334444:ssoinstance"},
        )

        self.sso_client_stubber.add_response(
            "describe_permission_set",
            {
                "PermissionSet": {
                    "CreatedDate": datetime.datetime.now().isoformat(),
                    "Description": "string",
                    "Name": "AWSReadOnlyAccess1",
                    "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb",
                    "RelayState": "string",
                    "SessionDuration": "string",
                }
            },
            {
                "InstanceArn": "arn:aws:iam::112223334444:ssoinstance",
                "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-72238dcf2af4d70c/ps-ee56096dded3dd82",
            },
        )

        self.sso_client_stubber.add_response(
            "describe_permission_set",
            {
                "PermissionSet": {
                    "CreatedDate": datetime.datetime.now().isoformat(),
                    "Description": "string",
                    "Name": "AWSReadOnlyAccess",
                    "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb",
                    "RelayState": "string",
                    "SessionDuration": "string",
                }
            },
            {
                "InstanceArn": "arn:aws:iam::112223334444:ssoinstance",
                "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-72238dcf2af4d70c/ps-1cf71c9d3ac397d2",
            },
        )

        self.sso_client_stubber.add_response(
            "describe_permission_set",
            {
                "PermissionSet": {
                    "CreatedDate": datetime.datetime.now().isoformat(),
                    "Description": "string",
                    "Name": "AWSReadOnlyAccess2",
                    "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb",
                    "RelayState": "string",
                    "SessionDuration": "string",
                }
            },
            {
                "InstanceArn": "arn:aws:iam::112223334444:ssoinstance",
                "PermissionSetArn": "arn:aws:sso:::permissionSet/ssoins-72238dcf2af4d70c/ps-63fe84230b679882",
            },
        )

        self.sso_client_stubber.activate()
        with patch.object(handler.SsoService, "__init__", self.empty_class_init):
            sso = handler.SsoService({})
            sso.client = self.sso_client
            sso.get_sso_data()
            responce = sso.get_permission_sets()
        assert sso.instance_arn == "arn:aws:iam::112223334444:ssoinstance"
        assert sso.identity_store_id == "d-2b57a3f2cb"
        assert sso.permission_sets != None
        sso.get_permission_sets = Mock()
        sso.get_permission_sets.return_value = responce
        return sso
