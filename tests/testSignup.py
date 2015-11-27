import unittest
import uuid
from .MockContext import MockContext
import src.signup.index
import src.signin.index

class SignupTest(unittest.TestCase):
    def test_signup(self):
        identity = str(uuid.uuid4())

        res = src.signup.index.handler(
            {
                'IdentityId': identity,
                'id': identity,
                'identifier': '',
                'provider': 'test',
                'firstname': 'First',
                'lastname': 'Last',
                'displayName': 'First Last',
                'email_address': 'test@domain.invalid'
            },
            MockContext('signup', '$LATEST')
        )

        res2 = src.signin.index.handler(
            {
                'IdentityId': identity
            },
            MockContext('signin', '$LATEST')
        )

        self.assertEquals('success', res2['status'])
        self.assertEquals('login successful', res2['msg'])
        self.assertEquals(identity, res2['data']['IdentityId'])
