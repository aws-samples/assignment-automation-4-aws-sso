#!/usr/bin/env python3
import os
import sys

from aws_cdk import App, Environment

from enterprise_sso.enterprise_aws_sso_cdkpipelines import EnterpriseSSOPipelineStack

app = App()

context: dict = app.node.try_get_context("enterprise_sso")
deployment_account_id: str = context.get("enterprise_sso_deployment_account_id")
region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION"))

if not region:
    print("Please set AWS_DEFAULT_REGION or AWS_REGION")
    sys.exit(1)


EnterpriseSSOPipelineStack(
    app,
    "EnterpriseAWSSSOPipelineStack",
    env=Environment(account=deployment_account_id, region=region),
)

app.synth()
