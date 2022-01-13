# Enterprise AWS SSO

## Architecture Overview

![architecture](sso_assignments.png)

## Deployment notes

1. Modify cdk.context.json with appropriate accounts information as well as variables and commit changes. Main ones are:
    - *enterprise_sso_management_account_id*: AWS Account Id of the AWS Organization Management Account
    - *enterprise_sso_exec_account_id*: AWS Account Id where the application will be running in. Should NOT be the same as the AWS Organization management account.
    - *enterprise_sso_deployment_account_id*: AWS Account Id that will have the AWS CodePipeline pipeline deployed to.
1. Set `AWS_DEFAULT_REGION` environment variables to the desired value
1. Bootstrap all AWS accounts using the new bootstrap style. More information [here](https://docs.aws.amazon.com/cdk/api/latest/docs/pipelines-readme.html#cdk-environment-bootstrapping):
    1. Bootstrap deployment account:

        ```sh
        env CDK_NEW_BOOTSTRAP=1 npx cdk bootstrap \
        --profile deployment_profile \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        aws://111111111111/us-east-1
        ```

    1. Bootstrap management account:

        ```sh
        env CDK_NEW_BOOTSTRAP=1 npx cdk bootstrap \
        --profile management_profile \
        --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        --trust 11111111111 \
        aws://222222222222/us-east-2
        ```

    1. Bootstrap iam account:

        ```sh

        env CDK_NEW_BOOTSTRAP=1 npx cdk bootstrap \
        --profile iam_profile \
            --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
        --trust 11111111111 \
        aws://3333333333333/us-east-2
        ```

1. Setup environment variables for accessing the deployment AWS account.
1. For an initial deployment, the initial_deployment.py script can be used, which creates a codecommit repository and pushes the code using settings from `cdk.context.json`.
    1. Install requirements from `initial-deploy-requirements.txt`
    1. Execute `initial_deployment.py`
        1. the `--no-history` flag can be used to not preserve git history if desired.
1. Once the repository exists and the code is pushed to it, execute `cdk deploy`. For all further changes, the newly created pipeline will be triggered for commits to the `main` branch.

## Usage

This solution is event driven, utilizing a custom AWS EventBridge EventBus in the IAM account (the name of the bus is defined in the `target_event_bus_name` context variable in `cdk.context.json`). The following following events are supported:

### Create/Remove AWS SSO records

In order to manipulate AWS SSO assignments following event structure is used:

```json
{
    "source": "permissionEventSource",
    "detail": {
        "permissions": [
            {
                "ActionType": "Add", //Possible values "Add" or "Remove"
                "PermissionFor": "OrganizationalUnit", //Possible values "OrganizationalUnit"|"Account"|"Tag"|"Root"
                "OrganizationalUnitName": "OU_Name",
                "AccountNumber": 30010047,
                "Tag": "key=value",
                "GroupName": "GroupX",
                "UserName": "User Name",
                "PermissionSetName": "AWSReadOnlyAccess"
            }
        ]
    }
}
```

Based on the type of user entity (user or group) and permission abstraction. Different fields are used.
Examples:

#### Add record for user and a single account

```json
{

    "source": "permissionEventSource",
    "detail": {
        "permissions": [
            {
                "ActionType": "Add",
                "PermissionFor": "Account"
                "AccountNumber": 1234567890123,
                "UserName": "User Name",
                "PermissionSetName": "AWSReadOnlyAccess"
            }
        ]
    }

}
```

#### Add record for Organization and group. It's important to use OU name and not not the ID

```json
{

    "source": "permissionEventSource",
    "detail": {
        "permissions": [
            {
                "ActionType": "Add",
                "PermissionFor": "OrganizationalUnit",
                "OrganizationalUnitName": "OU_Name",
                "GroupName": "GroupX",
                "PermissionSetName": "AWSReadOnlyAccess"
            }
        ]
    }

}
```

#### Remove record for Tag and group

```json
{

    "source": "permissionEventSource",
    "detail": {
        "permissions": [
            {
                "ActionType": "Remove",
                "PermissionFor": "Tag",
                "Tag": "key=value",
                "GroupName": "GroupX",
                "PermissionSetName": "AWSReadOnlyAccess"
            }
        ]
    }

}
```

Events mentioned above will create records in DynamoDB, and trigger corresponding action in AWS SSO.
DynamoDB acts as a single point of truth, for any following actions. Having such records in DynamoDB will allow automatic assignment/removal of AWS SSO permission when moving accounts between OU as well as creating new accounts in OU.

### DB Records example

![architecture](DynamoDB.png)

## Limitations

1. As of current state does not support nested OU's
1. Testing is currently limited
1. Support of ResourceTagged AWS Organization is removed for now due to multiple processing options

## Testing prerequisites

Python tests are executed using pytest package.
Make sure that folder ` ./src/layers/ ` is added to `PYTHONPATH` variable as test are depended on the code fined in lambda layers.

To execute test pass the test pass the test file to the pytest:

```bash
python3 -m pytest -v src
```

This will load mock classes from the layers folder and run complete test suite.

## Additional Info

This project is best executed from a virtualenv.

To manually create a virtualenv on MacOS and Linux:

```bash
python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```bash
source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```cmd
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```bash
pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```bash
cdk synth
```

## Useful commands

- `cdk ls` list all stacks in the app
- `cdk synth` emits the synthesized CloudFormation template
- `cdk deploy` deploy this stack to your default AWS account/region
- `cdk diff` compare deployed stack with current state
- `cdk docs` open CDK documentation

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
