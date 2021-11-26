from aws_cdk import core, aws_iam as iam, aws_events as events, aws_events_targets as targets


class EnterpriseAwsSsoManagementStack(core.Stack):
    def __init__(
        self, scope: core.Construct, construct_id: str, full_deployment: bool, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ## Getting parameters and setting defaults
        context: dict = self.node.try_get_context("enterprise_sso")

        enterprise_sso_exec_account_id: str = context.get("enterprise_sso_exec_account_id")
        enterprise_sso_read_only_role: str = context.get(
            "enterprise_sso_management_read_only_role",
            "assignment-management-read-only-role",
        )
        enterprise_sso_assignment_management_role: str = context.get(
            "enterprise_sso_management_role", "assignment-management-role"
        )
        target_event_bus_name: str = context.get("target_event_bus_name", "enterprise-aws-sso")
        target_event_bus_region: str = context.get("target_event_bus_region", self.region)

        if full_deployment or (self.region != "us-east-1" and not full_deployment):
            ### Permission management ###

            ## Read only role for assignment definition handler function ##
            identitystore_policy = iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "identitystore:DescribeUser",
                            "identitystore:ListUsers",
                            "identitystore:DescribeGroup",
                            "identitystore:ListGroups",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                    )
                ]
            )

            organizations_policy = iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["organizations:DescribeOrganizationalUnit", "tag:GetResources"],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                    )
                ]
            )

            self.management_enterprise_sso_read_only_role = iam.Role(
                self,
                "EnterpriseAWSSSOReadOnlyRole",
                role_name=enterprise_sso_read_only_role,
                inline_policies={
                    "identitystore-readonly": identitystore_policy,
                    "organizations-readonly": organizations_policy,
                },
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AWSSSOReadOnly")],
                assumed_by=iam.ArnPrincipal(
                    f"arn:aws:iam::{enterprise_sso_exec_account_id}:role/{enterprise_sso_read_only_role}"
                ),
            )

            ## Assignment management role for assignment execution function ##
            assignment_management_policy = iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "sso:CreateAccountAssignment",
                            "sso:ListPermissionSetsProvisionedToAccount",
                            "sso:ListInstances",
                            "sso:DeleteAccountAssignment",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        sid="IAMListPermissions",
                        actions=["iam:ListRoles", "iam:ListPolicies"],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        sid="AccessToSSOProvisionedRoles",
                        actions=[
                            "iam:AttachRolePolicy",
                            "iam:CreateRole",
                            "iam:DeleteRole",
                            "iam:DeleteRolePolicy",
                            "iam:DetachRolePolicy",
                            "iam:GetRole",
                            "iam:ListAttachedRolePolicies",
                            "iam:ListRolePolicies",
                            "iam:PutRolePolicy",
                            "iam:UpdateRole",
                            "iam:UpdateRoleDescription",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=["arn:aws:iam::*:role/aws-reserved/sso.amazonaws.com/*"],
                    ),
                    iam.PolicyStatement(
                        actions=["iam:GetSAMLProvider"],
                        effect=iam.Effect.ALLOW,
                        resources=["arn:aws:iam::*:saml-provider/AWSSSO_*_DO_NOT_DELETE"],
                    ),
                ]
            )

            self.management_enterprise_sso_assignment_management_role = iam.Role(
                self,
                "EnterpriseAWSSSOAssignmentManagementRole",
                role_name=enterprise_sso_assignment_management_role,
                inline_policies={
                    "enterprise-sso-assignment-management": assignment_management_policy
                },
                assumed_by=iam.ArnPrincipal(
                    f"arn:aws:iam::{enterprise_sso_exec_account_id}:role/{enterprise_sso_assignment_management_role}"
                ),
            )

        if (not full_deployment and self.region == "us-east-1") or full_deployment:
            ### Event bus configuration ###
            enterprise_sso_eventbus = events.EventBus.from_event_bus_arn(
                self,
                "enterpriseawsssoEventbus",
                event_bus_arn=f"arn:aws:events:{target_event_bus_region}:{enterprise_sso_exec_account_id}:event-bus/{target_event_bus_name}",
            )

            self.organizations_events_forwarding_rule = events.Rule(
                self,
                "OrganizationsEventsRule",
                description="Forward Organizations events to enterprise-aws-sso",
                event_pattern=events.EventPattern(
                    detail={
                        "eventName": [
                            "CreateAccountResult",
                            "MoveAccount",
                            "TagResource",
                            "UntagResource",
                        ]
                    },
                    detail_type=["AWS Service Event via CloudTrail", "AWS API Call via CloudTrail"],
                    source=["aws.organizations"],
                ),
                targets=[targets.EventBus(enterprise_sso_eventbus)],
            )

            # AWS SSO Events
            self.sso_events_forwarding_rule = events.Rule(
                self,
                "AWSSSOEventsRule",
                description="Forward CT events to enterprise-aws-sso",
                event_pattern=events.EventPattern(
                    detail={"eventName": ["CreatePermissionSet", "DeletePermissionSet"]},
                    detail_type=["AWS Service Event via CloudTrail", "AWS API Call via CloudTrail"],
                    source=["aws.sso"],
                ),
                targets=[targets.EventBus(enterprise_sso_eventbus)],
            )
