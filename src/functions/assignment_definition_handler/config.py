################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

from aws_assume_role_lib import assume_role
from sso.handler import SsoService
from orgz.handler import Organizations
from common.error import Error

import boto3
import os

LAMBDA_FUNC_NAME = "Assignment definition handler"


def load_config():
    # Following configuration is not use outside this function
    sso_admin_role_arn = os.getenv(
        "SSO_ADMIN_ROLE_ARN",
        "arn:aws:iam::112223334444:role/assignment-management-role",
    )
    sns_arn = os.getenv(
        "ERROR_TOPIC_NAME", "ERROR_TOPIC_NAME"
    )  # Getting the SNS Topic ARN passed in by the environment variables.

    controller = Config_object("This should act as a controller for all components")

    # Definig global clients
    controller.config = Config_object("Environment configuration")
    controller.config.queue_url = os.getenv("ASSIGNMENTS_QUEUE_URL", "test_queue")
    controller.config.map_key_name = os.getenv("ASSOCIATIONID_KEY_NAME", "mappingId")
    controller.config.map_sortkey_name = os.getenv("ASSOCIATIONID_SORT_KEY_NAME", "mappingValue")
    controller.config.table_name = os.environ.get(
        "ASSIGNMENTS_TABLE_NAME", "TEST_ASSIGNMENT_TABLE_NAME"
    )
    controller.config.associationid_concat_char = os.getenv("ASSOCIATIONID_CONCAT_CHAR", "|")

    controller.config.permission_set_status = "PermissionSetStatus"
    controller.config.permission_set_name = "PermissionSetName"

    # Boto configuraiton
    session = boto3.Session()
    assumed_role_session = assume_role(session, sso_admin_role_arn)

    # Clients
    controller.clients = Config_object("Client configuration")
    controller.clients.sso = SsoService(assumed_role_session)
    controller.clients.org = Organizations(role=assumed_role_session)
    controller.clients.identity_store = assumed_role_session.client("identitystore")
    controller.clients.dynamodb = session.client("dynamodb")
    controller.clients.dynamodb_table = session.resource("dynamodb").Table(
        controller.config.table_name
    )
    controller.clients.sqs = session.client("sqs")
    # Error handling
    controller.clients.error_handler = Error(
        sns_topic=sns_arn,
        session=session,
        lambda_func_name=LAMBDA_FUNC_NAME,
    )
    controller.clients.logger = controller.clients.error_handler.get_logger()

    # Datablocks
    controller.data = Config_object("Datablocks")
    controller.data.permission_sets = controller.clients.sso.get_permission_sets()
    controller.data.ACTION_TYPE_CREATE = "CREATE"
    controller.data.ACTION_TYPE_DELETE = "DELETE"
    controller.data.GROUP_PRINCIPAL_TYPE = "GROUP"
    controller.data.USER_PRINCIPAL_TYPE = "USER"

    return controller


class Config_object(object):
    def __init__(self, *args):
        self.__header__ = str(args[0]) if args else None

    def __repr__(self):
        if self.__header__ is None:
            return super(Config_object, self).__repr__()
        return self.__header__

    def next(self):
        raise StopIteration

    def __iter__(self):
        keys = self.__dict__.keys()
        for key in keys:
            if not key.startswith("__") and not isinstance(key, Config_object):
                yield getattr(self, key)

    def __len__(self):
        keys = self.__dict__.keys()
        return len(
            [key for key in keys if not key.startswith("__") and not isinstance(key, Config_object)]
        )
