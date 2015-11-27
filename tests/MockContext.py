import functools
import random
import uuid
import boto3

class MockContext(object):
    def __init__(self, name, version):
        self.function_name = name
        self.function_version = version
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:{name}:{version}".format(name=name, version=version))
        self.memory_limit_in_mb = float('inf')
        self.log_group_name = 'test-group'
        self.log_stream_name = 'test-stream'
        self.client_context = None

        self.aws_request_id = '-'.join(map(
            lambda n: ''.join(map(lambda _: random.choice('0123456789abcdef'), range(0, n))),
            [8, 4, 4, 4, 12]
        ))

        # Get an identity ID
        self.identity = lambda: None
        self.identity.cognito_identity_pool_id = 'us-east-1:xxxxxxxx-e8a3-xxxx-abf2-xxxxxxxxxxxxxx'

        res = boto3.client('cognito-identity').get_open_id_token_for_developer_identity(
            IdentityPoolId=self.identity.cognito_identity_pool_id,
            Logins={
                'login.lambdamock.test': 'test-user'
            },
        )

        self.identity.cognito_identity_id = res['IdentityId']
        print "\nYOUR Cognito IdentityId is: "
        print "--------------------------\n"+self.identity.cognito_identity_id
        print "\nResults:\n--------"

    def get_remaining_time_in_millis(self):
        return float('inf')
