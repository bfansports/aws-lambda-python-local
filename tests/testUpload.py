import unittest
import requests
from .MockContext import MockContext
import src.asset_upload.index
import src.asset_upload_finish.index

class UploadTest(unittest.TestCase):
    def test_validupload(self):
        res = src.asset_upload.index.handler(
            {
                "org_id": "TT",
                "event_id": "0db69fda7820941a",
                "name": "test.jpg",
                "size": 1024,
                "type": "image/jpeg"
            },
            MockContext('asset_upload', '$LATEST')
        )

        parts = []
        for part, url in res['upload_urls'].iteritems():
            info = requests.put(url, data='\0' * int(res['chunk_size']))
            parts.append({
                'ETag': info.headers['etag'],
                'PartNumber': part
            })

        res2 = src.asset_upload_finish.index.handler(
            {
                'encode_id': res['encode_id'],
                'parts': parts
            },
            MockContext('asset_upload_finish', '$LATEST')
        )

        self.assertEquals(res['encode_id'], res2['encode_id'])
        self.assertEquals('"81485c0e873d222199469076b60f30e9-1"', res2['ETag'])
