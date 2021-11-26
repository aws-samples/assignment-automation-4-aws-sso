#!/usr/bin/env python3
import boto3
import json
import logging
from aws_cdk import core

from enterprise_sso.enterprise_aws_sso_stack import EnterpriseAwsSsoExecStack
from enterprise_sso.enterprise_aws_sso_management_stack import (
    EnterpriseAwsSsoManagementStack,
)

app = core.App()


enterprise_sso = EnterpriseAwsSsoExecStack(app, "AssignmentManagementIAM")

enterprise_sso_management = EnterpriseAwsSsoManagementStack(app, "AssignmentManagementRoot")

app.synth()
