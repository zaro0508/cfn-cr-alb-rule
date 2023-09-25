import json
import os
import unittest
from unittest.mock import MagicMock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from ruler import app


class TestNextPriority(unittest.TestCase):

  false_listener_arn = 'arn:aws:elasticloadbalancing:us-east-1:012345678901:listener/app/sc135-poc/bf54cc972d64237b/8ad4c71091181c61'
  mock_elbv2_response_empty = {"Rules": []}
  # truncated version of an actual rule response
  mock_elbv2_response_not_empty = {
    "Rules": [
      { "Priority": "3" },
      { "Priority": "1" },
      { "Priority": "2" }
    ]
  }


  @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'test-region'})
  def test_next_priority_empty_rules(self):
    elbv2 = boto3.client('elbv2')
    with Stubber(elbv2) as stubber:
      app.get_client = MagicMock(return_value=elbv2)
      stubber.add_response('describe_rules', self.mock_elbv2_response_empty)
      result = app.next_priority(self.false_listener_arn)
      expected = 1 # if there are no rules the priority should be 1
      self.assertEqual(result, expected)


  @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'test-region'})
  def test_next_priority_not_empty_rules(self):
    elbv2 = boto3.client('elbv2')
    with Stubber(elbv2) as stubber:
      app.get_client = MagicMock(return_value=elbv2)
      stubber.add_response('describe_rules', self.mock_elbv2_response_not_empty)
      result = app.next_priority(self.false_listener_arn)
      expected = 4 # expect highest priority + 1
      self.assertEqual(result, expected)


  @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'test-region'})
  def test_next_priority_client_error(self):
    elbv2 = boto3.client('elbv2')
    with Stubber(elbv2) as stubber, self.assertRaises(Exception) as context_manager:
      stubber.add_client_error(
        method='describe_rules',
        service_error_code='ListenerNotFound')
      app.get_client = MagicMock(return_value=elbv2)
      result = app.next_priority(self.false_listener_arn)
    expected_error = f'{app.ALB_RULES_ACCESS_ERROR}: listener_arn={self.false_listener_arn}; ListenerNotFound'
    self.assertEqual(str(context_manager.exception), expected_error)
