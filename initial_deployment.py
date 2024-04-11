#!/usr/bin/env python3
import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time

import boto3
from git import Repo

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def main():
    logging.info(f"Trying to create Codecommit repository {codecommit_repository_name}")
    try:
        repo_response = cc_client.create_repository(repositoryName=codecommit_repository_name)
        logging.info("Repository successfully created. Continuing with initial deployment")
    except cc_client.exceptions.RepositoryNameExistsException as e:
        logging.warning("Repository already exists. Checking if empty")
        try:
            commits = cc_client.get_branch(
                repositoryName=codecommit_repository_name,
                branchName=codecommit_repository_branch_name,
            )
            logging.error(
                "Repository already created and is not empty. Application might already be deployed."
            )
            sys.exit(1)
        except cc_client.exceptions.BranchDoesNotExistException as e:
            logging.info(
                "Repository exists, but looks to be empty. Continuing with initial deployment"
            )
            pass

    repository_url = f"codecommit::{region}://{codecommit_repository_name}"

    if args.no_history:
        with tempfile.TemporaryDirectory() as tmpdirname:
            repo_path = shutil.copytree(
                app_source_path,
                f"{tmpdirname}/{codecommit_repository_name}",
                ignore=shutil.ignore_patterns("cdk.out", ".git", "*.pyc"),
            )
            repo = Repo.init(
                repo_path, bare=False, initial_branch=codecommit_repository_branch_name
            )
            repo.git.add(all=True)
            repo.index.commit("initial commit")
            logging.info(repo_path)
            os.listdir(repo_path)
    else:
        repo = Repo(app_source_path)

    remote = repo.create_remote(remote_name, url=repository_url, allow_unsafe_protocols=True)

    # if args.no_history:
    #     time.sleep(60)

    remote.push(codecommit_repository_branch_name)
    logging.info("You can now run 'cdk deploy' to deploy the pipeline.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-nh", "--no-history", action="store_true")
    args = parser.parse_args()
    logging.info(f"Loading cdk context")
    with open(f"cdk.context.json") as cdk_context_file:
        cdk_context = json.load(cdk_context_file)["enterprise_sso"]

    cc_client = boto3.client("codecommit")
    codecommit_repository_name = cdk_context.get("codecommit_repository_name", "enterprise-aws-sso")
    codecommit_repository_branch_name = cdk_context.get("codecommit_repository_branch_name", "main")
    remote_name = "codecommit"

    region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION"))

    if not region:
        logging.error("Please set AWS_DEFAULT_REGION or AWS_REGION")
        sys.exit(1)

    app_source_path = os.path.dirname(os.path.realpath(__file__))
    main()
