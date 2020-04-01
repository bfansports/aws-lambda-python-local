import functools
import random
import uuid
import boto3
import copy
from lib import env
from lib import common

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

        self.aws_request_id = '-'.join([''.join([random.choice('0123456789abcdef') for _ in range(0, n)]) for n in [8, 4, 4, 4, 12]])

        # # Get an identity ID
        self.identity = lambda: None
        self.identity.cognito_identity_pool_id = env.IDENTITY_POOL
        self.identity.cognito_identity_id = common.get_identity()

        if (self.identity.cognito_identity_id is False):
            print("Get new Identity from Cognito")

            # Get Cognito identity
            res = boto3.client('cognito-identity').get_id(
                AccountId=env.AWS_ACCOUNT_ID,
                IdentityPoolId=env.IDENTITY_POOL
            )
            self.identity.cognito_identity_id = res['IdentityId']
            # Cache identity
            common.put_identity(self.identity.cognito_identity_id)

        print("\nYOUR Cognito IdentityId is: ")
        print(("--------------------------\n"+self.identity.cognito_identity_id))
        print("\nResults:\n--------")

    def get_remaining_time_in_millis(self):
        return float('inf')


class MockContextUnitTest(object):

    IDENTITY_POOL_ID = env.IDENTITY_POOL

    def __init__(self, name, version):
        self.function_name = name
        self.function_version = version
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:{name}:{version}".format(name=name, version=version))
        self.memory_limit_in_mb = float('inf')
        self.log_group_name = 'test-group'
        self.log_stream_name = 'test-stream'
        self.client_context = None

        self.aws_request_id = '-'.join([''.join([random.choice('0123456789abcdef') for _ in range(0, n)]) for n in [8, 4, 4, 4, 12]])
    def get_remaining_time_in_millis(self):
        return float('inf')

def _add_cognito_id(obj):
    obj.identity.cognito_identity_id = boto3.client('cognito-identity').get_open_id_token_for_developer_identity(
            IdentityPoolId=MockContextUnitTest.IDENTITY_POOL_ID,
            Logins={
                'login.sportarchive.test': 'test-user'
            },
        )['IdentityId']

def get_context(name, version):
    context = MockContextUnitTest(name, version)
    context.identity = lambda: None
    context.identity.cognito_identity_pool_id = MockContextUnitTest.IDENTITY_POOL_ID
    _add_cognito_id(context)
    return context

def get_context_false_user(name, version):
    context = MockContextUnitTest(name, version)
    context.identity = lambda: None
    context.identity.cognito_identity_pool_id = MockContextUnitTest.IDENTITY_POOL_ID
    context.identity.cognito_identity_id = '123456789'
    return context

def get_context_no_identity(name, version):
    context = MockContextUnitTest(name, version)
    return context
