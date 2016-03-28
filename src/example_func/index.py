from lib import common
from env import common

def handler(event, context):
    try:

        # event contains your intput data
        # context contains your context information.
        # (IdentityId and more)

        CognitoIdentityID = context.identity.cognito_identity_id

        # Do your thing. Return JSON data.
        
    except common.SAError as e:
        print e # log
        raise Exception('error: custom_failed')
    except KeyError as e:
        # IdentityId missing in 'event' ?
        print common.SAError("accessing unknown property")
        raise Exception('error: property_failed')
    except Exception as e:
        print common.SAError("unknown error of type %s" % type(e))
        raise Exception('error: generic_failed')
    
    return data.json
