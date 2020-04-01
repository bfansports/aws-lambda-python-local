#!/usr/bin/env python

import argparse
import sys
import traceback
import boto3
from lib import apiconnect
from lib import common

# Parse CLI arguments
parser = argparse.ArgumentParser(description='Run a Lambda function locally.')
parser.add_argument('--verbose', '-v', action='count', default=0,
                    help='Show more output (one -v for WARNING, two for INFO, three for DEBUG)')
parser.add_argument('--noauth', action='count', default=0,
                    help='Use a new identity even if .idendity file exists')
parser.add_argument('--method', '-m', type=str, required=True,
                    help='HTTP Method to use to connect')
parser.add_argument('--path', '-p', type=str, required=True, 
                    help='/path at the end of hostname')
parser.add_argument('--query', '-q', type=str, 
                    help='Api endpoint to append to baseurl.')
parser.add_argument('--input', '-i', metavar='FILE', type=argparse.FileType('r'), nargs='?',
                    default=sys.stdin,
                    help='File to get input from, or "-" for stdin')
args = parser.parse_args()

try:
    api = apiconnect.ApiConnect(args.verbose, args.noauth)
    
    print("method: "+args.method)
    print("path: "+args.path)
    query = ''
    if args.query is not None:
        query = args.query
        print("query: "+args.query)

    payload = common.get_payload(args.input, api.IdentityId)
    print("payload: "+payload)
            
    api.callApi(args.method, args.path, payload, query)

except Exception as e:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    response = {
        'errorMessage': str(exc_value),
        'stackTrace': traceback.extract_tb(exc_traceback),
        'errorType': exc_type.__name__
    }
    del exc_traceback
    

