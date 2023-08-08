from aws_cdk import Stage
from constructs import Construct
from enterprise_sso.enterprise_aws_sso_management_stack import EnterpriseAwsSsoManagementStack


class EnterpriseAwsSsoManagementStage(Stage):
    def __init__(
        self, scope: Construct, construct_id: str, full_deployment: bool, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        enterprise_aws_sso_management = EnterpriseAwsSsoManagementStack(
            self, "EnterpriseAWSSSOManagement", full_deployment=full_deployment
        )
