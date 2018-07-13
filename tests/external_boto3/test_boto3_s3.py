import sys
import uuid

import boto3
import botocore
import moto

from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics

# patch moto to support py37
if sys.version_info >= (3, 7):
    import re
    moto.packages.responses.responses.re._pattern_type = re.Pattern

AWS_ACCESS_KEY_ID = 'AAAAAAAAAAAACCESSKEY'
AWS_SECRET_ACCESS_KEY = 'AAAAAASECRETKEY'
AWS_REGION_NAME = 'us-west-2'

TEST_BUCKET = 'python-agent-test-%s' % uuid.uuid4()

BOTOCORE_VERSION = tuple(map(int, botocore.__version__.split('.')))
if BOTOCORE_VERSION < (1, 7, 41):
    S3_URL = 's3-us-west-2.amazonaws.com'
else:
    S3_URL = 's3.us-west-2.amazonaws.com'

_s3_scoped_metrics = [
    ('External/%s/botocore/GET' % S3_URL, 2),
    ('External/%s/botocore/PUT' % S3_URL, 2),
    ('External/%s/botocore/DELETE' % S3_URL, 2),
]

_s3_rollup_metrics = [
    ('External/all', 6),
    ('External/allOther', 6),
    ('External/%s/all' % S3_URL, 6),
    ('External/%s/botocore/GET' % S3_URL, 2),
    ('External/%s/botocore/PUT' % S3_URL, 2),
    ('External/%s/botocore/DELETE' % S3_URL, 2),
]


@validate_transaction_metrics(
        'test_boto3_s3:test_s3',
        scoped_metrics=_s3_scoped_metrics,
        rollup_metrics=_s3_rollup_metrics,
        background_task=True)
@background_task()
@moto.mock_s3
def test_s3():
    client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME,
    )

    # Create bucket
    resp = client.create_bucket(Bucket=TEST_BUCKET)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # Put object
    resp = client.put_object(
            Bucket=TEST_BUCKET,
            Key='hello_world',
            Body=b'hello_world_content'
    )
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200

    # List bucket
    resp = client.list_objects(Bucket=TEST_BUCKET)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    assert len(resp['Contents']) == 1
    assert resp['Contents'][0]['Key'] == 'hello_world'

    # Get object
    resp = client.get_object(Bucket=TEST_BUCKET, Key='hello_world')
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 200
    assert resp['Body'].read() == b'hello_world_content'

    # Delete object
    resp = client.delete_object(Bucket=TEST_BUCKET, Key='hello_world')
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 204

    # Delete bucket
    resp = client.delete_bucket(Bucket=TEST_BUCKET)
    assert resp['ResponseMetadata']['HTTPStatusCode'] == 204