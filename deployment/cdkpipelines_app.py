#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from enterprise_sso.enterprise_aws_sso_cdkpipelines import EnterpriseSSOPipelineStack

app = cdk.App()

context: dict = app.node.try_get_context("enterprise_sso")
deployment_account_id: str = context.get("enterprise_sso_deployment_account_id")
region = os.environ.get("AWS_DEFAULT_REGION", os.environ["AWS_REGION"])


EnterpriseSSOPipelineStack(
    app,
    "EnterpriseAWSSSOPipelineStack",
    env=cdk.Environment(account=deployment_account_id, region=region),
)

app.synth()
