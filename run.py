#!/usr/bin/env python

import argparse
import importlib
import json
import logging
import sys
import traceback
import tests.MockContext
import lib

# Parse CLI arguments
parser = argparse.ArgumentParser(description='Run a Lambda function locally.')
parser.add_argument('--verbose', '-v', action='count', default=0,
                    help='Show more output (one -v for WARNING, two for INFO, three for DEBUG)')
parser.add_argument('name', metavar='NAME', type=str, nargs='?',
                    help='Name of the function to be run')
parser.add_argument('input', metavar='FILE', type=argparse.FileType('r'), nargs='?', default=sys.stdin,
                    help='File to get input from, or "-" for stdin')
args = parser.parse_args()

# Set up context
response = ''
context = tests.MockContext.MockContext(args.name, '$LATEST')
logging.basicConfig(
    stream=sys.stderr,
    format=("[%(levelname)s]\t%(asctime)s\t{req}\t%(message)s").format(req=context.aws_request_id),
    datefmt="%Y-%m-%dT%H:%M:%S%Z",
    level=(logging.ERROR - args.verbose * 10)
)

try:
    # Run the function
    module = importlib.import_module('src.{name}.index'.format(name=args.name))
    response = module.handler(json.load(args.input), context)
except Exception as exc:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    response = {
        'errorMessage': str(exc_value),
        'stackTrace': traceback.extract_tb(exc_traceback),
        'errorType': exc_type.__name__
    }
    del exc_traceback

print json.dumps(response, indent=4, separators=(',', ': '))
