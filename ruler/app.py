import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from crhelper import CfnResource

MISSING_PROPERTY_ERROR_MESSAGE = 'Parameter is required'
MISSING_ENVIRONMENT_VARIABLE_MESSAGE = 'Environment variable is required'
MISSING_CLIENT_SECRET_KEY = 'OIDC Client secret key not found in AWS System Manager parameter store'
ALB_RULES_ACCESS_ERROR = 'Problem retrieving AWS application load balancer rules'
ALB_RULE_CREATION_ERROR = 'Problem creating AWS application load balancer rule'

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

helper = CfnResource(
  json_logging=False, log_level='DEBUG', boto_level='DEBUG')


def get_variables(func, var_names, error_msg):
  '''Generic method to extract values and raise error if they are missing'''
  values = []

  for var_name in var_names:
    value = func(var_name)
    if not value:
      raise ValueError(f'{error_msg}: {var_name}')
    values.append(value)

  return values


def get_properties(event):
  '''Extract properites of interest from the lambda-triggering event'''
  resource_properties = event.get('ResourceProperties')
  param_names = ['InstanceId', 'TargetGroupArn', 'ListenerArn']
  variables = get_variables(resource_properties.get, param_names, MISSING_PROPERTY_ERROR_MESSAGE)
  return variables


def get_envvars():
  '''Extract environment variables'''
  env_var_names = [
    'OIDC_CLIENT_SECRET_KEYNAME',
    'OIDC_ISSUER',
    'OIDC_AUTHORIZATION_ENDPOINT',
    'OIDC_TOKEN_ENDPOINT',
    'OIDC_USER_INFO_ENDPOINT',
    'OIDC_CLIENT_ID'
  ]
  return get_variables(os.getenv, env_var_names, MISSING_ENVIRONMENT_VARIABLE_MESSAGE)


def get_client(service):
  return boto3.client(service)


def get_client_key(key_name):
  '''Retrieve OIDC secret key from AWS System Manager'''
  ssm = get_client('ssm')
  try:
    response = ssm.get_parameter(
      Name=key_name,
      WithDecryption=True)
  except ClientError as e:
    client_error_msg = e.response['Error']['Code']
    exception_msg = f'{MISSING_CLIENT_SECRET_KEY}: key_name={key_name}; {client_error_msg}'
    raise Exception(exception_msg)

  return response['Parameter']['Value']


def next_priority(listener_arn):
  '''Determine the next priority value for an ALB listener rule'''
  elbv2 = get_client('elbv2')
  try:
    rules = elbv2.describe_rules(ListenerArn=listener_arn).get('Rules')
  except ClientError as e:
    client_error_msg = e.response['Error']['Code']
    exception_msg = f'{ALB_RULES_ACCESS_ERROR}: listener_arn={listener_arn}; {client_error_msg}'
    raise Exception(exception_msg)

  priorities = sorted([int(rule['Priority']) for rule in rules if rule['Priority'] != 'default'])
  priority = 1 if not priorities else priorities[-1] + 1
  log.debug(f'Next priority value = {priority}')
  return priority


@helper.update
def update(event, context):
  '''Handles custom resource update events'''
  logger.info('Received update event:' + json.dumps(event, sort_keys=False))
  delete(event, context)
  physical_resource_id = create(event, context)
  return physical_resource_id


@helper.create
def create(event, context):
  '''Handles customm resource create events'''
  log.info('Start ALB rule-making Lambda processing')
  log.debug('Received create event: ' + json.dumps(event, sort_keys=False))

  # get variables from lambda properties and environment
  instance_id, target_group_arn, listener_arn = get_properties(event)
  oidc_client_secret_key_name, oidc_issuer, oidc_auth_endpoint, oidc_token_endpoint, oidc_user_info_endpoint, oidc_client_id  = get_envvars()

  # get oidc client secret from ssm
  client_secret = get_client_key(oidc_client_secret_key_name)

  # determine priority for the next rule by checking existing alb listener rules
  priority = next_priority(listener_arn)

  # create the rule
  elbv2 = get_client('elbv2')
  try:
    response = elbv2.create_rule(
      ListenerArn=listener_arn,
      Priority=priority,
      Conditions=[
        {
          "Field": "path-pattern",
          "PathPatternConfig": {
              "Values": [f"/{instance_id}/*"]
          }
        }
      ],
      Actions=[
        {
          "Type": "authenticate-oidc",
          "AuthenticateOidcConfig": {
            "Issuer": oidc_issuer,
            "AuthorizationEndpoint": oidc_auth_endpoint,
            "TokenEndpoint": oidc_token_endpoint,
            "UserInfoEndpoint": oidc_user_info_endpoint,
            "ClientId": oidc_client_id,
            "ClientSecret": client_secret,
            "AuthenticationRequestExtraParams": {
              "claims": "{\"id_token\":{\"userid\":{\"essential\":true}},\"userinfo\":{\"userid\":{\"essential\":true}}}"
            },
            "OnUnauthenticatedRequest": "authenticate"
          },
          "Order": 1
        },
        {
          "Type": "forward",
          "TargetGroupArn": target_group_arn,
          "Order": 2
        }
      ]
    )
  except ClientError as e:
    client_error_msg = e.response['Error']['Code']
    exception_msg = f'{ALB_RULE_CREATION_ERROR}; {client_error_msg}'
    raise Exception(exception_msg)

  log.debug('Received create rule response from elv2: ' + json.dumps(response, sort_keys=False))
  physical_resource_id = response.get('Rules')[0].get('RuleArn')
  return physical_resource_id


@helper.delete
def delete(event, context):
  '''Handles custom resource delete events'''
  log.debug('Received delete event: ' + json.dumps(event, sort_keys=False))
  elbv2 = get_client('elbv2')
  rule_arn = event['PhysicalResourceId']
  try:
    response = elbv2.delete_rule(RuleArn=rule_arn)
    log.debug(json.dumps(response))
  except ClientError as e:
    log.debug(e.response['Error']['Message'])


def handler(event, context):
  '''Lambda handler, invokes custom resource helper'''
  helper(event, context)
