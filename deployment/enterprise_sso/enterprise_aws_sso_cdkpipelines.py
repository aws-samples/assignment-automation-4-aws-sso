from aws_cdk import Stack
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, CodeBuildStep
from constructs import Construct
from enterprise_sso.enterprise_aws_sso_management_stage import EnterpriseAwsSsoManagementStage
from enterprise_sso.enterprise_aws_sso_stage import EnterpriseAwsSsoExecStage


class EnterpriseSSOPipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        context: dict = self.node.try_get_context("enterprise_sso")

        management_account_id: str = context.get("enterprise_sso_management_account_id")
        sso_exec_account_id: str = context.get("enterprise_sso_exec_account_id")
        codecommit_repository_name: str = context.get("codecommit_repository_name")
        codecommit_repository_branch_name: str = context.get("codecommit_repository_branch_name")

        codecommit_repository = codecommit.Repository.from_repository_name(
            self, "enterprisessorepo", codecommit_repository_name
        )

        pipeline = CodePipeline(self, "EnterpriseSSOCDKPipeline",
                        pipeline_name="EnterpriseSSOCDKPipeline",
                        synth=CodeBuildStep("Synth",
                            input=CodePipelineSource.code_commit(codecommit_repository, codecommit_repository_branch_name),
                            build_environment=codebuild.BuildEnvironment(privileged=True),
                            commands=["npm install -g aws-cdk",
                                "python -m pip install -r requirements.txt",
                                "cdk synth"]
                        )
                    )

        full_deployment = True if self.region == "us-east-1" else False

        # AWS SSO Exec Stage
        pipeline.add_stage(
            EnterpriseAwsSsoExecStage(
                self,
                "EnterpriseAWSSSOExec",
                env={
                    "account": sso_exec_account_id,
                    "region": self.region,
                },
            )
        )

        # AWS SSO Management Stage
        pipeline.add_stage(
            EnterpriseAwsSsoManagementStage(
                self,
                "EnterpriseAWSSSOManagemenent",
                full_deployment=full_deployment,  # full_deployment parameter
                env={
                    "account": management_account_id,
                    "region": self.region,
                },
            )
        )

        if self.region != "us-east-1":
            pipeline.add_stage(
                EnterpriseAwsSsoManagementStage(
                    self,
                    "EnterpriseAWSSSOManagemenentUsEast1",
                    False,  # full_deployment parameter
                    env={
                        "account": management_account_id,
                        "region": "us-east-1",
                    },
                )
            )
