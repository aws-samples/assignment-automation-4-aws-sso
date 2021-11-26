################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

import datetime
import unittest


from unittest.mock import patch, Mock
from botocore.stub import Stubber
from botocore.session import Session
from aws_lambda_powertools import Logger

from .. import handler

logger = Logger()


class TestOrgLayer(unittest.TestCase):  # pylint: disable=R0904,C0116
    """Class used for testing Organizations layer"""

    session = Session()
    org_client = session.create_client("organizations")
    org_client_stubber = Stubber(org_client)
    org_root_id = None

    """
    This method is used to override the actuall init function of a class in order to receive objects with all class methods.
    Such appraoch allows to redefine boto3 clients with mocks and test/use this class as a mock
    """

    def empty_class_init(self, role):
        pass

    with patch.object(handler.Organizations, "__init__", empty_class_init):
        organizations = handler.Organizations({})
        organizations.client = org_client
        organizations.account_ids = []

    def test_0_get_ou_root_id(self):
        self.org_client_stubber.add_response(
            "list_roots",
            {
                "Roots": [
                    {
                        "Id": "r-12id",
                        "Arn": "string",
                        "Name": "string",
                        "PolicyTypes": [
                            {
                                "Type": "SERVICE_CONTROL_POLICY",  # |'TAG_POLICY'|'BACKUP_POLICY'|'AISERVICES_OPT_OUT_POLICY',
                                "Status": "ENABLED",  #'ENABLED'|'PENDING_ENABLE'|'PENDING_DISABLE'
                            },
                        ],
                    },
                ],
                "NextToken": "string",
            },
            {},
        )

        self.org_client_stubber.activate()
        get_ou_root_id_responce = self.organizations.get_ou_root_id()
        assert get_ou_root_id_responce == "r-12id"
        self.org_root_id = get_ou_root_id_responce
        self.organizations.get_ou_root_id = Mock()
        self.organizations.get_ou_root_id.return_value = get_ou_root_id_responce

    def test_1_get_child_ous(self):
        self.org_client_stubber.add_response(
            "list_organizational_units_for_parent",
            {
                "OrganizationalUnits": [
                    {"Id": "pathid", "Arn": "string", "Name": "path"},
                ],
            },
            {"ParentId": "r-12id"},
        )
        self.org_client_stubber.activate()
        responce_list = list(self.organizations.get_child_ous("r-12id"))
        assert responce_list[0]["Id"] == "pathid"
        assert responce_list[0]["Name"] == "path"
        self.organizations.get_child_ous = Mock()
        self.organizations.get_child_ous.return_value = responce_list

    def test_2_get_accounts_for_parent(self):
        self.org_client_stubber.add_response(
            "list_accounts_for_parent",
            {
                "Accounts": [
                    {
                        "Id": "12345678990",
                        "Arn": "string",
                        "Email": "string",
                        "Name": "string",
                        "Status": "ACTIVE",
                        "JoinedMethod": "CREATED",
                        "JoinedTimestamp": datetime.datetime.now().isoformat(),
                    },
                    {
                        "Id": "12345678992",
                        "Arn": "string",
                        "Email": "string",
                        "Name": "string",
                        "Status": "ACTIVE",
                        "JoinedMethod": "CREATED",
                        "JoinedTimestamp": datetime.datetime.now().isoformat(),
                    },
                    {
                        "Id": "12345678993",
                        "Arn": "string",
                        "Email": "string",
                        "Name": "string",
                        "Status": "ACTIVE",
                        "JoinedMethod": "CREATED",
                        "JoinedTimestamp": datetime.datetime.now().isoformat(),
                    },
                ],
            },
            {"ParentId": "pathid"},
        )
        self.org_client_stubber.activate()
        responce = list(self.organizations.get_accounts_for_parent("pathid"))
        assert responce[0]["Id"] == "12345678990"
        assert responce[1]["Id"] == "12345678992"
        assert responce[2]["Id"] == "12345678993"
        self.organizations.get_accounts_for_parent = Mock()
        self.organizations.get_accounts_for_parent.return_value = responce

    def test_3_dir_to_ou(self):
        responce = list(self.organizations.dir_to_ou("/path"))
        assert responce[0]["Id"] == "12345678990"
        assert responce[1]["Id"] == "12345678992"
        assert responce[2]["Id"] == "12345678993"

    def test_4_get_account_ids(self):
        self.org_client_stubber.add_response(
            "list_accounts",
            {
                "Accounts": [
                    {
                        "Id": "12345678990",
                        "Arn": "string",
                        "Email": "string",
                        "Name": "string",
                        "Status": "ACTIVE",
                        "JoinedMethod": "CREATED",
                        "JoinedTimestamp": datetime.datetime.now().isoformat(),
                    },
                    {
                        "Id": "12345678992",
                        "Arn": "string",
                        "Email": "string",
                        "Name": "string",
                        "Status": "ACTIVE",
                        "JoinedMethod": "CREATED",
                        "JoinedTimestamp": datetime.datetime.now().isoformat(),
                    },
                    {
                        "Id": "12345678993",
                        "Arn": "string",
                        "Email": "string",
                        "Name": "string",
                        "Status": "ACTIVE",
                        "JoinedMethod": "CREATED",
                        "JoinedTimestamp": datetime.datetime.now().isoformat(),
                    },
                ],
            },
            {},
        )
        self.org_client_stubber.activate()
        responce = self.organizations.get_accounts_ids()
        assert responce[0] == "12345678990"
        assert responce[1] == "12345678992"
        assert responce[2] == "12345678993"
        self.organizations.get_accounts_ids = Mock()
        self.organizations.get_accounts_ids.return_value = responce

    def test_5_get_active_accounts_for_path(self):
        responce = list(self.organizations.get_active_accounts_for_path("/path"))
        assert responce[0] == "12345678990"
        assert responce[1] == "12345678992"
        assert responce[2] == "12345678993"

    def test_6_list_parents(self):

        self.org_client_stubber.add_response(
            "list_parents",
            {"Parents": [{"Id": "string", "Type": "string"}]},
        )
        response = self.organizations.list_parents("ou_id")
        self.organizations.list_parents = Mock()
        self.organizations.list_parents.return_value = response

    def test_7_describe_ou_name(self):

        self.org_client_stubber.add_response(
            "describe_organizational_unit",
            {"OrganizationalUnit": {"Arn": "stringstringARN", "Id": "string", "Name": "string"}},
        )
        response = self.organizations.describe_ou_name("ou_id")
        self.organizations.describe_ou_name = Mock()
        self.organizations.describe_ou_name.return_value = response

    def test_8_describe_account(self):

        self.org_client_stubber.add_response(
            "describe_account",
            {
                "Account": {
                    "Arn": "string",
                    "Email": "string",
                    "Id": "string",
                    "JoinedMethod": "string",
                    "JoinedTimestamp": 123456,
                    "Name": "string",
                    "Status": "string",
                }
            },
        )
        response = self.organizations.describe_account("account_id")
        self.organizations.describe_account = Mock()
        self.organizations.describe_account.return_value = response

    def get_mocked_org(self):
        self.test_0_get_ou_root_id()
        self.test_1_get_child_ous()
        self.test_2_get_accounts_for_parent()
        self.test_4_get_account_ids()
        self.test_6_list_parents()
        self.test_7_describe_ou_name()
        self.test_8_describe_account()
        return self.organizations
