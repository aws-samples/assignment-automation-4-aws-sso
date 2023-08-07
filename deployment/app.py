#!/usr/bin/env python3
import os
import sys

from aws_cdk import App, Environment

from enterprise_sso.enterprise_aws_sso_stack import EnterpriseAwsSsoExecStack
from enterprise_sso.enterprise_aws_sso_management_stack import (
    EnterpriseAwsSsoManagementStack,
)

app = App()

region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION"))
if not region:
    print("Please set AWS_DEFAULT_REGION or AWS_REGION")
    sys.exit(1)

full_deployment = True if region == "us-east-1" else False


enterprise_sso = EnterpriseAwsSsoExecStack(app, "AssignmentManagementIAM")

enterprise_sso_management = EnterpriseAwsSsoManagementStack(
    app, "AssignmentManagementRoot", full_deployment=full_deployment)

if region != 'us-east-1':
    enterprise_sso_management = EnterpriseAwsSsoManagementStack(
    app, "AssignmentManagementRootUsEast1", full_deployment=full_deployment, env=Environment(region='us-east-1')
)

app.synth()
