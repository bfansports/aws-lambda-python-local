import boto3
import botocore
import porc
import sys
import os
import json
import traceback
import requests
import string
from urllib2 import HTTPError
from lib import env

class SAError(Exception):
    def __init__(self, what):
        self.what = what
        
    def __str__(self):

        exc_type, exc_obj, exc_tb = sys.exc_info()
        tb = traceback.extract_tb(exc_tb)

        msg = "[ERROR] " + self.what + ': '
        for filename, lineno, name, line in tb:
            # Search for newline char
            msg += ('File \"%s\", line %d, in %s in \'%s\'\n' %
                (filename, lineno, name, line))

        return (msg)

def get_orchestrate_client():
    try:
        return porc.Client(env.ORCHESTRATE_KEY)
    except botocore.exceptions.ClientError as e:
        raise SAError(e.message)
    except botocore.exceptions.BotoCoreError as e:
        raise SAError(e.message)
    except:
        raise SAError("unknown_error")

# Used to catch some orchestrate error
def raise_for_status(res):
    try:
        res.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise SAError('%d => %s' % (e.response.status_code, e.response.reason))

# Get Payload from input and parses it
def get_payload(input, IdentityId, default=''):
    try:
        print "Enter your JSON input or Ctrl-D for no input:"
        payload = json.dumps(json.load(input))
        payload = json.loads(string.replace(payload, "%IDENTITY_ID%", IdentityId))
        payload = json.dumps(payload)
    except Exception as e:
        print e
        payload = default

    return payload

# Get identityID if any
def get_identity():
    if os.path.exists('.identity_'+env.CONFIG_MODE):            
        print "Get identity from cache file .identity"
        with open('.identity_'+env.CONFIG_MODE, 'r') as myfile:
            return myfile.read().replace('\n', '')
    return False

# Cache an identity
def put_identity(IdentityId):
    # Save identity in tmp file .identity
    myfile = open('.identity_'+env.CONFIG_MODE, 'w')
    myfile.write(IdentityId)
    myfile.close()
