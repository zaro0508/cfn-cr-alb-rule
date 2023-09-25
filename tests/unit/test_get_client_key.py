import json
import os
import unittest
from unittest.mock import MagicMock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from ruler import app


class TestGetClientKey(unittest.TestCase):

  mock_ssm_response = {
    "Parameter": {
        "Name": "/alb-notebook-access/AuthenticateOidcClientSecret",
        "Type": "SecureString",
        "Value": "not-the-real-key",
        "Version": 1,
        "LastModifiedDate": "2020-06-26T15:52:53.111000-07:00",
        "ARN": "arn:aws:ssm:us-east-1:012345678901:parameter/alb-notebook-access/AuthenticateOidcClientSecret",
        "DataType": "text"
    }
  }


  @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'test-region'})
  def test_get_client_key(self):
    ssm = boto3.client('ssm')
    with Stubber(ssm) as stubber:
      app.get_client = MagicMock(return_value=ssm)
      stubber.add_response('get_parameter', self.mock_ssm_response)
      test_key_name = 'not-the-real-key'
      result = app.get_client_key(test_key_name)
      self.assertEqual(result, test_key_name)


  @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'test-region'})
  def test_get_client_key_missing(self):
    ssm = boto3.client('ssm')
    with Stubber(ssm) as stubber, self.assertRaises(Exception) as context_manager:
      stubber.add_client_error(
        method='get_parameter',
        service_error_code='ParameterNotFound')
      app.get_client = MagicMock(return_value=ssm)
      test_key_name = 'not-the-real-key'
      result = app.get_client_key(test_key_name)
    expected_error = f'{app.MISSING_CLIENT_SECRET_KEY}: key_name={test_key_name}; ParameterNotFound'
    self.assertEqual(str(context_manager.exception), expected_error)
