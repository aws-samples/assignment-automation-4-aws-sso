from aws_cdk import core as cdk
from enterprise_sso.enterprise_aws_sso_management_stack import EnterpriseAwsSsoManagementStack


class EnterpriseAwsSsoManagementStage(cdk.Stage):
    def __init__(
        self, scope: cdk.Construct, construct_id: str, full_deployment: bool, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        enterprise_aws_sso_management = EnterpriseAwsSsoManagementStack(
            self, "EnterpriseAWSSSOManagement", full_deployment=full_deployment
        )
