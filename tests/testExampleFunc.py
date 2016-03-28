import unittest
import uuid
import copy
from .MockContext import MockContext
import MockContext
import src.example_func.index

def run_func(**keyword_args):
            return src.assets.index.handler(
                        keyword_args['event'],
                        keyword_args['context'])

class UsersAssets(unittest.TestCase):
            def test_one(self):
                        print "\n - test one"
                        context = MockContext.get_context('example_func', '$LATEST')
                        res = run_func(
                                    event = {
                                                "input1" : "0edf13a1de207c46"
                                    },
                                    context = context
                        )
