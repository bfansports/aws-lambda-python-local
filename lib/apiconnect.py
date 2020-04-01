# Get an Unauthenticated Cognito Identity
# Use it to connect to API Gateway

import sys, os, base64, datetime, hashlib, hmac 
import requests 
import boto3
import http.client
import logging
import json
import os.path
from lib import env
from lib import common

class ApiConnect(object):
    def __init__(self, verbose=0, noauth=0):

        if verbose == 1:
            http.client.HTTPConnection.debuglevel = 1
            
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
            
        self.IdentityId = common.get_identity()
        # We don't have a cached Identity. Get a new one
        if (noauth == 0 and self.IdentityId is False):
            print("Get new Identity from Cognito")
            # Get Cognito identity
            res = boto3.client('cognito-identity').get_id(
                AccountId=env.AWS_ACCOUNT_ID,
                IdentityPoolId=env.IDENTITY_POOL
            )
            self.IdentityId = res['IdentityId']
            # Cache identity
            common.put_identity(self.IdentityId)

        print("\nYOUR Cognito IdentityId is: ")
        print("--------------------------\n"+self.IdentityId)
        print("")

        # Get OpenId token to use for getting credentials
        res = boto3.client('cognito-identity').get_open_id_token(
            IdentityId=self.IdentityId
        )
        
        # Get temporary credentials
        res = boto3.client('cognito-identity').get_credentials_for_identity(
            IdentityId=self.IdentityId
        )
        
        self.access_key    = res['Credentials']['AccessKeyId']
        self.secret_key    = res['Credentials']['SecretKey']
        self.session_token = res['Credentials']['SessionToken']

    def sign(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def getSignatureKey(self, key, dateStamp, regionName, serviceName):
        kDate    = self.sign(('AWS4' + key).encode('utf-8'), dateStamp)
        kRegion  = self.sign(kDate, regionName)
        kService = self.sign(kRegion, serviceName)
        kSigning = self.sign(kService, 'aws4_request')
        return kSigning

    def callApi(self, method, path, payload, request_parameters=''):
        self.method = method
        self.host = env.API_HOST
        self.endpoint = env.API_ENDPOINT
        self.path = path
        self.request_parameters = request_parameters
        self.payload = payload
        self.service = 'execute-api'
        self.region = 'us-east-1'
        self.content_type = 'application/json'

        #print "Method: " + method
        #print "Path: " + path
        #print "Payload: " + payload
        #print "Param: " + request_parameters
        
        try:
            t = datetime.datetime.utcnow()
            amzdate = t.strftime('%Y%m%dT%H%M%SZ')
            datestamp = t.strftime('%Y%m%d') # Date w/o time, used in credential scope
            
            canonical_uri = env.API_STAGE + self.path
            canonical_querystring = self.request_parameters
            canonical_headers = 'host:' + self.host + '\n' + 'x-amz-date:' + amzdate + '\n' + 'x-amz-security-token:' + self.session_token + '\n'

            #print "Headers: " + canonical_headers
            
            signed_headers = 'host;x-amz-date;x-amz-security-token'
            
            payload_hash = hashlib.sha256(self.payload).hexdigest()
            
            canonical_request = self.method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash
            
            #print "Request: " + canonical_request
            
            algorithm = 'AWS4-HMAC-SHA256'
            credential_scope = datestamp + '/' + self.region + '/' + self.service + '/' + 'aws4_request'
            string_to_sign = algorithm + '\n' +  amzdate + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request).hexdigest()
            
            signing_key = self.getSignatureKey(self.secret_key, datestamp, self.region, self.service)
            
            signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()
            
            authorization_header = algorithm + ' ' + 'Credential=' + self.access_key + '/' + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature
            
            headers = {'Content-Type': self.content_type,
                       'X-Amz-Date': amzdate,
                       'X-Amz-Security-Token': self.session_token,
                       'Authorization': authorization_header}

            request_url = self.endpoint + canonical_uri
            if self.request_parameters != '':
                request_url += '?' + self.request_parameters
                
            print('\nBEGIN REQUEST')
            print("--------------------------\n"+request_url)
            
            if self.method == 'GET':
                r = requests.get(request_url, data=self.payload, headers=headers)
            elif self.method == 'POST':
                r = requests.post(request_url, data=self.payload, headers=headers)
            elif self.method == 'PUT':
                r = requests.put(request_url, data=self.payload, headers=headers)
            elif self.method == 'DELETE':
                r = requests.delete(request_url, data=self.payload, headers=headers)

            print('\nRESPONSE')
            print("--------------------------\nStatus Code: "+str(r.status_code))
            print(r.text)

            print('\nPRETTY JSON')
            print(json.dumps(json.loads(r.text), sort_keys=True, indent=4, separators=(',', ': ')))
    
        except Exception as e:
            print(e)
            
