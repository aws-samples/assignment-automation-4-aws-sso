################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################


from botocore.config import Config
from aws_lambda_powertools import Logger


"""
Paginator used with certain boto3 calls
when pagination is required
"""
logger = Logger()


def paginator(method, **kwargs):
    client = method.__self__
    iterator = client.get_paginator(method.__name__)
    for page in iterator.paginate(**kwargs).result_key_iters():
        for result in page:
            yield result


class Organizations:  # pylint: disable=R0904,C0116
    """Class used for modeling Organizations"""

    _config = Config(retries=dict(max_attempts=30))

    # As per configuration of ADF and actual deployments of organisation, defaulting org region to us-east-1.
    # To accomodate future developments, leaving this as a parameter which can be overwritten from the labmda.
    def __init__(self, role, account_id=None, region="us-east-1"):
        self.client = role.client("organizations", config=Organizations._config)
        self.tags_client = role.client(
            "resourcegroupstaggingapi",
            config=Organizations._config,
            region_name=region,
        )
        self.account_id = account_id
        self.account_ids = []
        self.root_id = None

    def get_parent_info(self):
        response = self.list_parents(self.account_id)
        return {
            "ou_parent_id": response.get("Id"),
            "ou_parent_type": response.get("Type"),
        }

    def enable_organization_policies(self, policy_type="SERVICE_CONTROL_POLICY"):  # or 'TAG_POLICY'
        try:
            self.client.enable_policy_type(RootId=self.get_ou_root_id(), PolicyType=policy_type)
        except self.client.exceptions.PolicyTypeAlreadyEnabledException:
            logger.info("%s are currently enabled within the Organization", policy_type)

    @staticmethod
    def trim_policy_path(policy):
        return policy[2:] if policy.startswith("//") else policy

    def get_organization_map(self, org_structure, counter=0):
        for name, ou_id in org_structure.copy().items():
            for organization_id in [
                organization_id["Id"]
                for organization_id in paginator(
                    self.client.list_children,
                    **{"ParentId": ou_id, "ChildType": "ORGANIZATIONAL_UNIT"},
                )
            ]:
                if organization_id in org_structure.values() and counter != 0:
                    continue
                ou_name = self.describe_ou_name(organization_id)
                trimmed_path = Organizations.trim_policy_path("{0}/{1}".format(name, ou_name))
                org_structure[trimmed_path] = organization_id
        counter = counter + 1
        # Counter is greater than 4 here is the conditional as organizations cannot have more than 5 levels of nested OUs
        return org_structure if counter > 4 else self.get_organization_map(org_structure, counter)

    def describe_ou_name(self, ou_id):
        try:
            response = self.client.describe_organizational_unit(OrganizationalUnitId=ou_id)
            return response["OrganizationalUnit"]["Name"]
        except Exception as exception:
            # If Exception occurs, parse Response and write it to Error Topic.
            # Then, raise exception to not delete the message from queue.
            logger.error("Error: OU is the Root of the Organization")
            logger.error("Exception: " + str(exception))
            raise (exception)

    def get_accounts_ids(self):
        for account in paginator(self.client.list_accounts):
            if not account.get("Status") == "ACTIVE":
                logger.warning("Account %s is not an Active AWS Account", account["Id"])
                continue
            self.account_ids.append(account["Id"])
        return self.account_ids

    def get_active_accounts_for_path(self, path):
        account_ids = []
        for account in self.dir_to_ou(path):
            if not account.get("Status") == "ACTIVE":
                logger.warning("Account %s is not an Active AWS Account", account["Id"])
                continue
            account_ids.append(account["Id"])
        return account_ids

    def describe_account(self, account_id):
        return self.client.describe_account(AccountId=account_id)

    @staticmethod
    def determine_ou_path(ou_path, ou_child_name):
        return "{0}/{1}".format(ou_path, ou_child_name) if ou_path else ou_child_name

    def list_parents(self, ou_id):
        return self.client.list_parents(ChildId=ou_id).get("Parents")[0]

    def get_accounts_for_parent(self, parent_id):
        return paginator(self.client.list_accounts_for_parent, ParentId=parent_id)

    def get_child_ous(self, parent_id):
        responce = paginator(self.client.list_organizational_units_for_parent, ParentId=parent_id)
        return responce

    def get_ou_root_id(self):
        return self.client.list_roots().get("Roots")[0].get("Id")

    def dir_to_ou(self, path):
        p = path.split("/")[1:]
        ou_id = self.get_ou_root_id()

        while p:
            for ou in self.get_child_ous(ou_id):
                if ou["Name"] == p[0]:
                    p.pop(0)
                    ou_id = ou["Id"]
                    break
            else:
                raise Exception("Path {0} failed to return a child OU at '{1}'".format(path, p[0]))
        else:
            return self.get_accounts_for_parent(ou_id)

    def build_account_path(self, ou_id, account_path, cache):
        """Builds a path tree to the account from the root of the Organization"""
        current = self.list_parents(ou_id)

        # While not at the root of the Organization
        while current.get("Type") != "ROOT":
            # check cache for ou name of id
            if not cache.check(current.get("Id")):
                cache.add(current.get("Id"), self.describe_ou_name(current.get("Id")))
            ou_name = cache.check(current.get("Id"))
            account_path.append(ou_name)
            return self.build_account_path(current.get("Id"), account_path, cache)
        return Organizations.determine_ou_path(
            "/".join(list(reversed(account_path))),
            self.describe_ou_name(self.get_parent_info().get("ou_parent_id")),
        )

    def get_account_ids_for_tags(self, tags):
        tag_filter = []
        for key, value in tags.items():
            if isinstance(value, list):
                values = value
            else:
                values = [value]
            tag_filter.append({"Key": key, "Values": values})
        account_ids = []
        for resource in paginator(
            self.tags_client.get_resources,
            TagFilters=tag_filter,
            ResourceTypeFilters=["organizations"],
        ):
            arn = resource["ResourceARN"]
            account_id = arn.split("/")[::-1][0]
            account_ids.append(account_id)
        return account_ids

    def list_organizational_units_for_parent(self, parent_ou):
        organizational_units = [
            ou
            for org_units in self.client.get_paginator(
                "list_organizational_units_for_parent"
            ).paginate(ParentId=parent_ou)
            for ou in org_units["OrganizationalUnits"]
        ]
        return organizational_units

    def get_account_id(self, account_name):
        for account in self.list_accounts():
            if account["Name"].strip() == account_name.strip():
                return account["Id"]

        return None

    def list_accounts(self):
        """Retrieves all accounts in organization."""
        existing_accounts = [
            account
            for accounts in self.client.get_paginator("list_accounts").paginate()
            for account in accounts["Accounts"]
        ]
        return existing_accounts

    def get_ou_id(self, ou_path, parent_ou_id=None):
        # Return root OU if '/' is provided
        if ou_path.strip() == "/":
            return self.root_id

        # Set initial OU to start looking for given ou_path
        if parent_ou_id is None:
            parent_ou_id = self.root_id

        # Parse ou_path and find the ID
        ou_hierarchy = ou_path.strip("/").split("/")
        hierarchy_index = 0

        while hierarchy_index < len(ou_hierarchy):
            org_units = self.list_organizational_units_for_parent(parent_ou_id)
            for ou in org_units:
                if ou["Name"] == ou_hierarchy[hierarchy_index]:
                    parent_ou_id = ou["Id"]
                    hierarchy_index += 1
                    break
            else:
                raise ValueError(
                    f"Could not find ou with name {ou_hierarchy} in OU list {org_units}."
                )

        return parent_ou_id
