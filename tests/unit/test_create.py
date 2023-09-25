import json
import os
import unittest
from unittest.mock import MagicMock, patch

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from ruler import app


class TestCreate(unittest.TestCase):

  mock_create_response = {"Rules":[{"RuleArn":"arn:aws:elasticloadbalancing:us-east-1:012345678901:listener-rule/app/sc135-poc/bf54cc972d64237b/8ad4c71091181c60/62caa6dfa73dbce8","Priority":"7","Conditions":[{"Field":"path-pattern","Values":["/i-049f8b7f35ef87673"],"PathPatternConfig":{"Values":["/i-049f8b7f35ef87673"]}}],"Actions":[{"Type":"forward","TargetGroupArn":"arn:aws:elasticloadbalancing:us-east-1:012345678901:targetgroup/TargetGroup-i-049f8b7f35ef87673/32ee340e330ca6e2","Order":2,"ForwardConfig":{"TargetGroups":[{"TargetGroupArn":"arn:aws:elasticloadbalancing:us-east-1:012345678901:targetgroup/TargetGroup-i-049f8b7f35ef87673/32ee340e330ca6e2","Weight":1}],"TargetGroupStickinessConfig":{"Enabled":False}}},{"Type":"authenticate-oidc","AuthenticateOidcConfig":{"Issuer":"https://repo-prod.prod.sagebase.org/auth/v1","AuthorizationEndpoint":"https://repo-prod.prod.sagebase.org/auth/v1","TokenEndpoint":"https://qtg2zn2bbf.execute-api.us-east-1.amazonaws.com/token","UserInfoEndpoint":"https://repo-prod.prod.sagebase.org/auth/v1/oauth2/userinfo","ClientId":"100050","SessionCookieName":"AWSELBAuthSessionCookie","Scope":"openid","SessionTimeout":604800,"AuthenticationRequestExtraParams":{"claims":"{\"id_token\":{\"userid\":{\"essential\":true}},\"userinfo\":{\"userid\":{\"essential\":true}}}"},"OnUnauthenticatedRequest":"authenticate"},"Order":1}],"IsDefault":False}]}
  mock_properties = [
    'i-049f8b7f35ef87673',
    'arn:aws:elasticloadbalancing:us-east-1:012345678901:targetgroup/TargetGroup-i-049f8b7f35ef87673/32ee340e330ca6e2',
    'arn:aws:elasticloadbalancing:us-east-1:012345678901:listener/app/sc135-poc/bf54cc972d64237b/8ad4c71091181c61'
  ]
  mock_envvars = [
    'secret-key-name',
    'issuer',
    'auth-endpoint',
    'token-endpoint',
    'user-info-endpoint',
    'client-id'
  ]


  @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'test-region'})
  @patch('ruler.app.get_properties', MagicMock(return_value=mock_properties))
  @patch('ruler.app.get_envvars', MagicMock(return_value=mock_envvars))
  @patch('ruler.app.get_client_key', MagicMock(return_value='not-the-real-key'))
  @patch('ruler.app.next_priority', MagicMock(return_value=7))
  def test_create(self):
    elbv2 = boto3.client('elbv2')
    with Stubber(elbv2) as stubber:
      app.get_client = MagicMock(return_value=elbv2)
      stubber.add_response('create_rule', self.mock_create_response)
      result = app.create({},{})
      expected_rule_arn = 'arn:aws:elasticloadbalancing:us-east-1:012345678901:listener-rule/app/sc135-poc/bf54cc972d64237b/8ad4c71091181c60/62caa6dfa73dbce8'
      self.assertEqual(result, expected_rule_arn)


  @patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'test-region'})
  @patch('ruler.app.get_properties', MagicMock(return_value=mock_properties))
  @patch('ruler.app.get_envvars', MagicMock(return_value=mock_envvars))
  @patch('ruler.app.get_client_key', MagicMock(return_value='not-the-real-key'))
  @patch('ruler.app.next_priority', MagicMock(return_value=7))
  def test_create_fail(self):
    elbv2 = boto3.client('elbv2')
    with Stubber(elbv2) as stubber, self.assertRaises(Exception) as context_manager:
      app.get_client = MagicMock(return_value=elbv2)
      stubber.add_client_error(
        method='create_rule',
        service_error_code='PriorityInUse')
      result = app.create({},{})
    expected_error = f'{app.ALB_RULE_CREATION_ERROR}; PriorityInUse'
    self.assertEqual(str(context_manager.exception), expected_error)
