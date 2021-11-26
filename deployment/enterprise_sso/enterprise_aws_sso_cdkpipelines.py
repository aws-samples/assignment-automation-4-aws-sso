from aws_cdk import core
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import pipelines
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codebuild as codebuild

from enterprise_sso.enterprise_aws_sso_stage import EnterpriseAwsSsoExecStage
from enterprise_sso.enterprise_aws_sso_management_stage import EnterpriseAwsSsoManagementStage


class EnterpriseSSOPipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        context: dict = self.node.try_get_context("enterprise_sso")

        management_account_id: str = context.get("enterprise_sso_management_account_id")
        sso_exec_account_id: str = context.get("enterprise_sso_exec_account_id")
        codecommit_repository_name: str = context.get("codecommit_repository_name")
        codecommit_repository_branch_name: str = context.get("codecommit_repository_branch_name")


        source_artifact = codepipeline.Artifact()
        cloud_assembly_artifact = codepipeline.Artifact()

        codecommit_repository = codecommit.Repository.from_repository_name(
            self, "enterprisessorepo", codecommit_repository_name
        )

        pipeline = pipelines.CdkPipeline(
            self,
            "EnterpriseSSOCDKPipeline",
            cloud_assembly_artifact=cloud_assembly_artifact,
            source_action=codepipeline_actions.CodeCommitSourceAction(
                action_name="Source",
                repository=codecommit_repository,
                output=source_artifact,
                branch=codecommit_repository_branch_name,
            ),
            synth_action=pipelines.SimpleSynthAction(
                source_artifact=source_artifact,
                cloud_assembly_artifact=cloud_assembly_artifact,
                environment=codebuild.BuildEnvironment(privileged=True),
                install_command="npm install -g aws-cdk@1.130.0 && pip install -r requirements.txt",
                # build_command="pytest unittests",
                synth_command="cdk synth",
            ),
        )

        full_deployment = True if self.region == "us-east-1" else False


        # AWS SSO Exec Stage
        pipeline.add_application_stage(
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
        pipeline.add_application_stage(
            EnterpriseAwsSsoManagementStage(
                self,
                "EnterpriseAWSSSOManagemenent",
                full_deployment=full_deployment, # full_deployment parameter
                env={
                    "account": management_account_id,
                    "region": self.region,
                },
            )
        )

        if self.region != "us-east-1":
            pipeline.add_application_stage(
                EnterpriseAwsSsoManagementStage(
                    self,
                    "EnterpriseAWSSSOManagemenentUsEast1",
                    False, # full_deployment parameter
                    env={
                        "account": management_account_id,
                        "region": "us-east-1",
                    },
                )
            )
