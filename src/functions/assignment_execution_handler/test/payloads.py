################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
################################################################################

event_input_data_create = {
    "Records": [
        {
            "messageId": "3769c1ec-6f65-49c1-966c-2be7732a0a1d",
            "receiptHandle": "AQEBZEJDt7kCNhTtZzI5/WCH4E7ArTzudBiU3u1IAystrGA9yx3wAg223Pg9xY6yBEXExnmW+PkcUbGJpfSvKaapgbidiBRHhNFCsSMOGGg0FFwkcwNo7WoN6xtLrQh+x+Vm6Rx/jvTupYN7lGFvUDHSgby25FTiLcMN3bBG8pbMShiFhe4RXK4hO0Gc/0gcq2rbj1INNUfm37KJa0v5KQqbHyAKXQ4WaaKkmRsuE//2OjFBqvqW3x2TBQ6YUtc576O2F0fm7kuB16ieNIyQQ7xRlfsjPXsQ4wZKKpjHqg0zfjBMeopENz762wAbFFxcaA1tqB5jcstuoL8DGSjFEFWtYkyUjNIzrtM3ttv3nx021MrDbXqQFw3egvoHPjg9p9ytpceakdb+6N3LgQ6cHXR6FQ==",
            "body": '{"PrincipalType": "string", "PrincipalId":"string","PermissionSetArn":"arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb","TargetId":"string", "Action":"CREATE"}',
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1626440153145",
                "SenderId": "AROAUX4IDK3FOMZSO2A5L:sgoeksel-Isengard",
                "ApproximateFirstReceiveTimestamp": "1626440153155",
            },
            "messageAttributes": {},
            "md5OfBody": "7e5e30491761e1993ecac5633a2c9621",
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-east-1:326166075082:AssignmentsQueue",
            "awsRegion": "us-east-1",
        }
    ]
}

event_input_data_delete = {
    "Records": [
        {
            "messageId": "3769c1ec-6f65-49c1-966c-2be7732a0a1d",
            "receiptHandle": "AQEBZEJDt7kCNhTtZzI5/WCH4E7ArTzudBiU3u1IAystrGA9yx3wAg223Pg9xY6yBEXExnmW+PkcUbGJpfSvKaapgbidiBRHhNFCsSMOGGg0FFwkcwNo7WoN6xtLrQh+x+Vm6Rx/jvTupYN7lGFvUDHSgby25FTiLcMN3bBG8pbMShiFhe4RXK4hO0Gc/0gcq2rbj1INNUfm37KJa0v5KQqbHyAKXQ4WaaKkmRsuE//2OjFBqvqW3x2TBQ6YUtc576O2F0fm7kuB16ieNIyQQ7xRlfsjPXsQ4wZKKpjHqg0zfjBMeopENz762wAbFFxcaA1tqB5jcstuoL8DGSjFEFWtYkyUjNIzrtM3ttv3nx021MrDbXqQFw3egvoHPjg9p9ytpceakdb+6N3LgQ6cHXR6FQ==",
            "body": '{"PrincipalType": "string", "PrincipalId":"string","PermissionSetArn":"arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb","TargetId":"string", "Action":"DELETE"}',
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1626440153145",
                "SenderId": "AROAUX4IDK3FOMZSO2A5L:sgoeksel-Isengard",
                "ApproximateFirstReceiveTimestamp": "1626440153155",
            },
            "messageAttributes": {},
            "md5OfBody": "7e5e30491761e1993ecac5633a2c9621",
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-east-1:326166075082:AssignmentsQueue",
            "awsRegion": "us-east-1",
        }
    ]
}

event_input_data_notsupportedaction = {
    "Records": [
        {
            "messageId": "3769c1ec-6f65-49c1-966c-2be7732a0a1d",
            "receiptHandle": "AQEBZEJDt7kCNhTtZzI5/WCH4E7ArTzudBiU3u1IAystrGA9yx3wAg223Pg9xY6yBEXExnmW+PkcUbGJpfSvKaapgbidiBRHhNFCsSMOGGg0FFwkcwNo7WoN6xtLrQh+x+Vm6Rx/jvTupYN7lGFvUDHSgby25FTiLcMN3bBG8pbMShiFhe4RXK4hO0Gc/0gcq2rbj1INNUfm37KJa0v5KQqbHyAKXQ4WaaKkmRsuE//2OjFBqvqW3x2TBQ6YUtc576O2F0fm7kuB16ieNIyQQ7xRlfsjPXsQ4wZKKpjHqg0zfjBMeopENz762wAbFFxcaA1tqB5jcstuoL8DGSjFEFWtYkyUjNIzrtM3ttv3nx021MrDbXqQFw3egvoHPjg9p9ytpceakdb+6N3LgQ6cHXR6FQ==",
            "body": '{"PrincipalType": "string", "PrincipalId":"string","PermissionSetArn":"arn:aws:sso:::permissionSet/ssoins-7223ac639f55e492/ps-504d6c2b57a3f2cb","TargetId":"string", "Action":"UPLOAD"}',
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1626440153145",
                "SenderId": "AROAUX4IDK3FOMZSO2A5L:sgoeksel-Isengard",
                "ApproximateFirstReceiveTimestamp": "1626440153155",
            },
            "messageAttributes": {},
            "md5OfBody": "7e5e30491761e1993ecac5633a2c9621",
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-east-1:326166075082:AssignmentsQueue",
            "awsRegion": "us-east-1",
        }
    ]
}
