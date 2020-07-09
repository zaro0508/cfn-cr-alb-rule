import json
import os
import unittest
from unittest.mock import MagicMock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from ruler import app


class TestGetVariables(unittest.TestCase):

  def test_properties_present(self):
    event = {
      'ResourceProperties': {
        'InstanceId': 'foo',
        'TargetGroupArn': 'bar',
        'ListenerArn': 'baz'
      }
    }
    results = app.get_properties(event)
    expected = ['foo', 'bar', 'baz']
    self.assertCountEqual(results, expected)


  def test_properties_missing(self):
    event = { 'ResourceProperties': {} }
    with self.assertRaises(ValueError) as context_manager:
      results = app.get_properties(event)
    expected_error = f'{app.MISSING_PROPERTY_ERROR_MESSAGE}: InstanceId'
    self.assertEqual(str(context_manager.exception), expected_error)


  def test_envvars_present(self):
    env_var_names = [
    'OIDC_CLIENT_SECRET_KEYNAME',
    'OIDC_ISSUER',
    'OIDC_AUTHORIZATION_ENDPOINT',
    'OIDC_TOKEN_ENDPOINT',
    'OIDC_USER_INFO_ENDPOINT',
    'OIDC_CLIENT_ID'
    ]

    vals = list(range(len(env_var_names)))
    for val in vals:
      os.environ[env_var_names[val]] = str(val)

    results = app.get_envvars()
    expected = [str(val) for val in vals]
    self.assertCountEqual(results, expected)


  def test_envars_missing(self):
    with self.assertRaises(ValueError) as context_manager:
      results = app.get_envvars()
    expected_error = f'{app.MISSING_ENVIRONMENT_VARIABLE_MESSAGE}: OIDC_CLIENT_SECRET_KEYNAME'
    self.assertEqual(str(context_manager.exception), expected_error)
