import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Mapping

import jsii
from aws_cdk import BundlingOptions, Duration, ILocalBundling, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as event_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as lambda_event_sources
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_sub
from aws_cdk import aws_sqs as sqs
from constructs import Construct


class EnterpriseAwsSsoExecStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        context: dict = self.node.try_get_context("enterprise_sso")

        management_account_id: str = context.get("enterprise_sso_management_account_id")
        sso_exec_account_id: str = context.get("enterprise_sso_exec_account_id")
        deployment_account_id: str = context.get("enterprise_sso_deployment_account_id")
        error_notification_email: str = context.get("error_notifications_email")
        sso_management_read_only_role: str = context.get(
            "enterprise_sso_management_read_only_role",
            "assignment-management-read-only-role",
        )
        sso_management_role: str = context.get(
            "enterprise_sso_management_role", "assignment-management-role"
        )
        target_event_bus_name: str = context.get("target_event_bus_name", "enterprise-aws-sso")
        sqs_delivery_delay_seconds: int = context.get(
            "assignment_processing_queue_delivery_delay_seconds", 30
        )
        sqs_visibility_timeout_seconds: int = context.get(
            "assignment_processing_queue_visibility_timeout_seconds", 300
        )
        lambda_defenition_handler_timeout_seconds: int = context.get(
            "assignment_defenition_handler_timeout_seconds", 300
        )
        lambda_execution_handler_timeout_seconds: int = context.get(
            "assignment_execution_handler_timeout_seconds", 300
        )
        assignment_processing_queue_name: str = context.get(
            "assignment_processing_queue_name", "assignment-processing-queue"
        )
        assignment_defenition_table_name: str = context.get(
            "assignment_defenition_table_name", "permission-assignments-table"
        )
        assignment_definition_table_partition_key: str = context.get(
            "assignment_definition_table_partition_key", "mappingId"
        )
        assignment_definition_table_sort_key: str = context.get(
            "assignment_definition_table_sort_key", "mappingValue"
        )

        lambda_runtime = _lambda.Runtime.PYTHON_3_10

        ## Event bus configuration
        self.ct_event_bus = events.EventBus(
            self,
            "CTEventBus",
            event_bus_name=target_event_bus_name,
        )
        events.CfnEventBusPolicy(
            self,
            "CTEventBusPolicy",
            statement_id="allow-management-account",
            action="events:PutEvents",
            event_bus_name=self.ct_event_bus.event_bus_name,
            principal=management_account_id,
        )

        events.CfnEventBusPolicy(
            self,
            "CTEventBusPolicyDeployment",
            statement_id="allow-deployment-account",
            action="events:PutEvents",
            event_bus_name=self.ct_event_bus.event_bus_name,
            principal=deployment_account_id,
        )

        events.CfnEventBusPolicy(
            self,
            "CTEventBusPolicyIAM",
            statement_id="allow-iam-account",
            action="events:PutEvents",
            event_bus_name=self.ct_event_bus.event_bus_name,
            principal=sso_exec_account_id,
        )

        ## Error notification topic
        self.error_notification_topic = sns.Topic(self, "ErrorNotificationTopic")
        self.error_notification_topic.add_subscription(
            sns_sub.EmailSubscription(error_notification_email)
        )
        self.sso_assignments_table = ddb.Table(
            self,
            assignment_defenition_table_name,
            partition_key=ddb.Attribute(
                name=assignment_definition_table_partition_key,
                type=ddb.AttributeType.STRING,
            ),
            sort_key=ddb.Attribute(
                name=assignment_definition_table_sort_key, type=ddb.AttributeType.STRING
            ),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            encryption=ddb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            stream=ddb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        ## assignment task queue
        self.assignment_processing_queue = sqs.Queue(
            self,
            "assignment-processing-queue",
            queue_name=assignment_processing_queue_name,
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            delivery_delay=Duration.seconds(sqs_delivery_delay_seconds),
            visibility_timeout=Duration.seconds(sqs_visibility_timeout_seconds),
        )

        ## Permission management part
        sqs_publish_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "sqs:SendMessage",
                        "sqs:SendMessageBatch",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[self.assignment_processing_queue.queue_arn],
                )
            ]
        )

        ## Permission management part
        eventbus_publish_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["events:PutEvents"],
                    effect=iam.Effect.ALLOW,
                    resources=[
                        self.ct_event_bus.event_bus_arn,
                    ],
                )
            ]
        )

        ## Service Event Handler role
        self.service_event_handler_role = self._create_lambda_role(
            role_id="ServiceEventHandlerRole",
            inline_policies={"eventbus": eventbus_publish_policy},
            managed_policy_name_list=[
                "service-role/AWSLambdaBasicExecutionRole",
            ],
        )

        ## DB Assignment Handler policy
        dynamodb_publish_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["dynamodb:BatchWrite*", "dynamodb:Update*", "dynamodb:PutItem"],
                    effect=iam.Effect.ALLOW,
                    resources=[
                        self.sso_assignments_table.table_arn,
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "dynamodb:BatchWrite*",
                        "dynamodb:Update*",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:DeleteItem",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[self.sso_assignments_table.table_arn],
                ),
            ]
        )

        ## DB Assignment Handler role
        self.db_assignment_handler_role = self._create_lambda_role(
            role_id="DBAssignmentHandlerRole",
            inline_policies={"dynamodb": dynamodb_publish_policy},
            managed_policy_name_list=[
                "service-role/AWSLambdaBasicExecutionRole",
            ],
        )

        ## Assignment management role for assignment execution function ##
        assignment_exec_policy = iam.PolicyDocument(
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
                    sid="AllowPublishingToSns",
                    actions=["sns:Publish"],
                    effect=iam.Effect.ALLOW,
                    resources=[self.error_notification_topic.topic_arn],
                ),
            ]
        )

        ## Assignment definition handler role
        self.assignment_handler_role = self._create_lambda_role(
            role_id="AssignmentDefinitionHandlerRole",
            role_name=sso_management_read_only_role,
            inline_policies={
                "sqs-publish-policy": sqs_publish_policy,
                "dynamodb": dynamodb_publish_policy,
            },
            managed_policy_name_list=[
                "service-role/AWSLambdaBasicExecutionRole",
            ],
            lambda_assume_roles_arn_list=[
                f"arn:aws:iam::{management_account_id}:role/{sso_management_read_only_role}"
            ],
        )

        ## Assignment execution handler role
        self.assignment_exec_role = self._create_lambda_role(
            role_id="AssignmentExecRole",
            role_name=sso_management_role,
            inline_policies={
                "assignment-policy": assignment_exec_policy,
            },
            managed_policy_name_list=[
                "service-role/AWSLambdaSQSQueueExecutionRole",
            ],
            lambda_assume_roles_arn_list=[
                f"arn:aws:iam::{management_account_id}:role/{sso_management_role}"
            ],
        )

        # Lambda Layer Paths
        common_layer_path = Path("src/layers/common")
        orgz_layer_path = Path("src/layers/orgz")
        sso_layer_path = Path("src/layers/sso")

        # Lambda Layers
        self.common_lambda_layer = _lambda.LayerVersion(
            self,
            "CommonLambdaLayer",
            code=_lambda.Code.from_asset(
                path=str(common_layer_path),
                bundling=BundlingOptions(
                    local=LocalBundler(str(common_layer_path)),
                    image=lambda_runtime.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        """pip --no-cache-dir install -r requirements.txt -t /asset-output/python && cp -au . /asset-output/python""",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_runtime],
        )

        self.org_lambda_layer = _lambda.LayerVersion(
            self,
            "OrganizationsLambdaLayer",
            code=_lambda.Code.from_asset(
                path=str(orgz_layer_path),
                bundling=BundlingOptions(
                    local=LocalBundler(str(orgz_layer_path)),
                    image=lambda_runtime.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        """pip --no-cache-dir install -r requirements.txt -t /asset-output/python && cp -au . /asset-output/python""",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_runtime],
        )

        self.sso_lambda_layer = _lambda.LayerVersion(
            self,
            "SsoLambdaLayer",
            code=_lambda.Code.from_asset(
                path=str(sso_layer_path),
                bundling=BundlingOptions(
                    local=LocalBundler(str(sso_layer_path)),
                    image=lambda_runtime.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        """pip --no-cache-dir install -r requirements.txt -t /asset-output/python && cp -au . /asset-output/python""",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_runtime],
        )

        # This function will process external events and manage DB records.
        self.db_assignment_handler = _lambda.Function(
            self,
            "DBAssignmentHandler",
            runtime=lambda_runtime,
            handler="index.handler",
            memory_size=256,
            role=self.db_assignment_handler_role,
            code=_lambda.Code.from_asset(
                path=str(Path("src/functions/assignment_db_handler")),
            ),
            layers=[
                self.common_lambda_layer,
            ],
            environment={
                "ERROR_TOPIC_NAME": self.error_notification_topic.topic_arn,
                "ASSIGNMENTS_TABLE_NAME": self.sso_assignments_table.table_name,
                "ASSOCIATIONID_KEY_NAME": assignment_definition_table_partition_key,
                "ASSOCIATIONID_SORT_KEY_NAME": assignment_definition_table_sort_key,
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "enterprise-aws-sso",
            },
        )

        self.db_assignments_lifecycle_events_rule = events.Rule(
            self,
            "DBAssignmentsEventsRule",
            description="Forward record creation events",
            enabled=True,
            event_bus=self.ct_event_bus,
            event_pattern=events.EventPattern(source=["permissionEventSource"]),
            rule_name=f"Forwarding-to-db-assignment-handler",
            targets=[event_targets.LambdaFunction(self.db_assignment_handler)],
        )

        # This function will process AWS Service Events and create application specific ones
        self.service_event_handler = _lambda.Function(
            self,
            "ServiceEventHandler",
            runtime=lambda_runtime,
            handler="index.handler",
            memory_size=256,
            role=self.service_event_handler_role,
            code=_lambda.Code.from_asset(
                path=str(Path("src/functions/service_event_handler")),
            ),
            layers=[
                self.common_lambda_layer,
            ],
            environment={
                "ERROR_TOPIC_NAME": self.error_notification_topic.topic_arn,
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "enterprise-aws-sso",
                "IAM_EVENT_BRIDGE_ARN": self.ct_event_bus.event_bus_arn,
            },
        )

        self.service_lifecycle_events_rule = events.Rule(
            self,
            "ServiceEventHandlerEventsRule",
            description="Forward AWS Service Events",
            enabled=True,
            event_bus=self.ct_event_bus,
            event_pattern=events.EventPattern(
                detail_type=["AWS Service Event via CloudTrail", "AWS API Call via CloudTrail"],
            ),
            rule_name=f"Forwarding-to-service-event-handler",
            targets=[event_targets.LambdaFunction(self.service_event_handler)],
        )

        # This function will define the assignments from the metadata in DynamoDB
        self.assignment_definition_handler = _lambda.Function(
            self,
            "AssignmentDefinitionHandler",
            runtime=lambda_runtime,
            handler="index.handler",
            memory_size=256,
            timeout=Duration.seconds(lambda_defenition_handler_timeout_seconds),
            role=self.assignment_handler_role,
            code=_lambda.Code.from_asset(
                path=str(Path("src/functions/assignment_definition_handler")),
            ),
            layers=[
                self.common_lambda_layer,
                self.org_lambda_layer,
                self.sso_lambda_layer,
            ],
            environment={
                "ASSIGNMENTS_TABLE_NAME": self.sso_assignments_table.table_name,
                "ASSIGNMENTS_QUEUE_URL": self.assignment_processing_queue.queue_url,
                "ERROR_TOPIC_NAME": self.error_notification_topic.topic_arn,
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "enterprise-sso",
                "ASSOCIATIONID_CONCAT_CHAR": "|",
                "ASSOCIATIONID_KEY_NAME": assignment_definition_table_partition_key,
                "ASSOCIATIONID_SORT_KEY_NAME": assignment_definition_table_sort_key,
                "SSO_ADMIN_ROLE_ARN": f"arn:aws:iam::{management_account_id}:role/{sso_management_read_only_role}",
            },
        )

        self.assignment_defenition_events_rule = events.Rule(
            self,
            "AssignmentDefenitionEventsRule",
            description="Forward Events",
            enabled=True,
            event_bus=self.ct_event_bus,
            event_pattern=events.EventPattern(
                account=[sso_exec_account_id], source=["enterprise-aws-sso"]
            ),
            rule_name=f"Forwarding-to-defenition-handler",
            targets=[event_targets.LambdaFunction(self.assignment_definition_handler)],
        )

        # setting the assignments topic as the event source for the execution lambda
        self.assignment_definition_handler.add_event_source(
            lambda_event_sources.DynamoEventSource(
                table=self.sso_assignments_table,
                starting_position=_lambda.StartingPosition.TRIM_HORIZON,
                batch_size=5,
                bisect_batch_on_error=True,
                on_failure=lambda_event_sources.SnsDlq(self.error_notification_topic),
                retry_attempts=3,
            )
        )

        self.sso_assignments_table.grant_read_data(
            self.assignment_definition_handler
        )  # TODO: not sure if needed
        self.sso_assignments_table.grant_stream_read(self.assignment_definition_handler)

        # This function will execute the assignments prepared by defenition lambda
        self.assignment_execution_handler = _lambda.Function(
            self,
            "AssignmentExecutionHandler",
            runtime=lambda_runtime,
            handler="index.handler",
            memory_size=256,
            timeout=Duration.seconds(lambda_execution_handler_timeout_seconds),
            role=self.assignment_exec_role,
            code=_lambda.Code.from_asset(
                path=str(Path("src/functions/assignment_execution_handler")),
            ),
            layers=[
                self.common_lambda_layer,
                self.sso_lambda_layer,
            ],
            environment={
                "ERROR_TOPIC_NAME": self.error_notification_topic.topic_arn,
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "enterprise-sso",
                "ASSOCIATIONID_CONCAT_CHAR": "|",
                "SSO_ADMIN_ROLE_ARN": f"arn:aws:iam::{management_account_id}:role/{sso_management_role}",
                "MANAGEMENT_ACCOUNT_ID": management_account_id,
            },
        )

        # setting the assignments queue as the event source for the execution lambda
        self.assignment_execution_handler.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.assignment_processing_queue, batch_size=10, max_concurrency=2
            )
        )

    def _create_lambda_role(
        scope: Construct,
        role_id: str,
        role_name: str = None,
        managed_policy_name_list: List[str] = None,
        lambda_assume_roles_arn_list: List[str] = None,
        inline_policies: Mapping[str, iam.PolicyDocument] = None,
    ):
        lambda_role = iam.Role(
            scope,
            id=role_id,
            role_name=role_name,
            inline_policies=inline_policies,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name)
                for managed_policy_name in managed_policy_name_list
            ],
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        if lambda_assume_roles_arn_list is not None:
            sts_policy = iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                effect=iam.Effect.ALLOW,
                resources=lambda_assume_roles_arn_list,
            )
            lambda_role.add_to_principal_policy(sts_policy)
        return lambda_role


@jsii.implements(ILocalBundling)
class LocalBundler:
    """This allows packaging lambda functions without the use of Docker"""

    def __init__(self, source_root):
        self.source_root = source_root

    def try_bundle(self, output_dir: str, options: BundlingOptions) -> bool:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "--version"])
        except:
            return False

        python_output_dir = str(Path(output_dir, "python"))
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "--no-cache-dir",
                "install",
                "-r",
                str(Path(self.source_root, "requirements.txt")),
                "-t",
                python_output_dir,
            ]
        )

        def copytree(src: str, dst: str, symlinks=False, ignore=None):
            for item in os.listdir(src):
                source_item = os.path.join(src, item)
                destination_item = os.path.join(dst, item)
                if os.path.isdir(source_item):
                    shutil.copytree(source_item, destination_item, symlinks, ignore)
                else:
                    shutil.copy2(source_item, destination_item)

        copytree(self.source_root, python_output_dir)

        return True
