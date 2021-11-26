################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError


class Error:  # pylint: disable=R0904
    def __init__(self, session, sns_topic: str, lambda_func_name: str) -> None:
        self.sns_session = session.client("sns")
        self.logger = Logger()
        self.sns_topic = sns_topic
        self.lambda_func_name = lambda_func_name

    def get_logger(self):
        return self.logger

    def publish_error_message(
        self,
        error_data_trace,
        error_msg,
    ):
        try:
            message = ""
            message += "\nLambda error  summary" + "\n\n"
            message += "##########################################################\n"
            message += "# Error data:- " + str(error_data_trace) + "\n"
            message += "# Log Message:- " + "\n"
            message += "# \t\t" + str(error_msg.split("\n")) + "\n"
            message += "##########################################################\n"

            # Sending the notification...
            self.sns_session.publish(
                TargetArn=self.sns_topic,
                Subject=f"Execution error for Lambda - {self.lambda_func_name}",
                Message=message,
            )
        except ClientError as e:
            self.logger.error("An error occurred: %s" % e)
