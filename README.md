# cfn-cr-alb-rule
Cloudformation Custom Resource that creates a listener
[rule](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-update-rules.html)
for an AWS ALB. The rule contains two actions. The first is an authentication
action; the second rule forwards to a target group, containing only a single
instance, if the first rule succeeds.

Inventory of source code and supporting files:

- ruler - Code for the application's Lambda function.
- events - Invocation events that you can use to invoke the function.
- tests - Unit tests for the application code.
- template.yaml - A template that defines the application's AWS resources.

The [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) is used to build and package the lambda code.
The [sceptre](https://github.com/Sceptre/sceptre) utility is used to deploy the
macro that invokes the lambda as a CloudFormation stack.

## Use in a Cloudformation Template
In addition to creating the ALBListenerRule custom resource, also required is
a target group with a single target, the EC2 instance. It is necessary to create
the target group so that the ALB can route to the instance if authentication
succeeds.

Here's an example, inserted into a stack that contains an
[AWS::EC2::Instance](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-instance.html)
resource with the Logical ID `LinuxInstance`. It also refers to several other
resources defined outside:
* `VpcId`: this uses an imported value from the VPC that is home to the ALB
* `ServiceToken`: this uses the Lambda function ARN
* `ListenerArn`: the ARN of a [listener](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html) created for the ALB

```yaml
  EC2TargetGroup:
    Type: AWS::ElasticLoadBalancingV2::TargetGroup
    Properties:
      Name: !Sub 'TargetGroup-${LinuxInstance}'
      HealthCheckIntervalSeconds: 30
      HealthCheckProtocol: HTTP
      HealthCheckTimeoutSeconds: 15
      HealthyThresholdCount: 5
      Matcher:
        HttpCode: '200'
      Port: 443
      Protocol: HTTPS
      TargetGroupAttributes:
      - Key: deregistration_delay.timeout_seconds
        Value: '20'
      Targets:
      - Id: !Ref LinuxInstance
        Port: 443
      UnhealthyThresholdCount: 3
      VpcId: !ImportValue
        'Fn::Sub': '${AWS::Region}-${VpcName}-VPCId'
      Tags:
      - Key: Name
        Value: !Sub 'TargetGroup-${LinuxInstance}'
  AlbListenerRule:
    Type: Custom::ALBListenerRule
    Properties:
      ServiceToken: !ImportValue
        'Fn::Sub': '${AWS::Region}-cfn-cr-alb-rule-FunctionArn'
      InstanceId: !Ref LinuxInstance
      TargetGroupArn: !Ref EC2TargetGroup
      ListenerArn: 'arn:aws:elasticloadbalancing:us-east-1:465877038949:listener/app/sc135-poc/bf54cc972d64237b/8ad4c71091181c60'
```

The creation of the custom resource triggers the lambda. The lambda makes
several AWS API calls in order to create a listener rule. First, it pulls a
secret key from AWS System Manager for the OIDC client. Second, it pulls all
existing rules to calculate the priority. Finally,  it creates the rule with
the actions as described above.

## Development

### Contributions
Contributions are welcome.

### Requirements
Run `pipenv install --dev` to install both production and development
requirements, and `pipenv shell` to activate the virtual environment. For more
information see the [pipenv docs](https://pipenv.pypa.io/en/latest/).

After activating the virtual environment, run `pre-commit install` to install
the [pre-commit](https://pre-commit.com/) git hook.

### Create a local build

```shell script
$ sam build --use-container
```

### Run locally

```shell script
$ sam local invoke ALBListenerRuleFunction --event events/create.json
```

### Run unit tests
Tests are defined in the `tests` folder in this project. Use PIP to install the
[pytest](https://docs.pytest.org/en/latest/) and run unit tests.

```shell script
$ python -m pytest tests/ -v
```

## Deployment

### Build

```shell script
sam build
```

## Deploy Lambda to S3
This requires the correct permissions to upload to bucket
`bootstrap-awss3cloudformationbucket-19qromfd235z9` and
`essentials-awss3lambdaartifactsbucket-x29ftznj6pqw`

```shell script
sam package --template-file .aws-sam/build/template.yaml \
  --s3-bucket essentials-awss3lambdaartifactsbucket-x29ftznj6pqw \
  --output-template-file .aws-sam/build/cfn-cr-alb-rule.yaml

aws s3 cp .aws-sam/build/cfn-cr-alb-rule.yaml s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/cfn-cr-alb-rule/master/
```

## Install Lambda into AWS
Create the following [sceptre](https://github.com/Sceptre/sceptre) file,
changing the parameters to match the values for your OIDC client.

config/prod/cfn-cr-alb-rule.yaml
```yaml
template_path: "remote/cfn-cr-alb-rule.yaml"
stack_name: "cfn-cr-alb-rule"
parameters:
  OidcClientSecretKeyName: '/alb-notebook-access/AuthenticateOidcClientSecret'
  OidcIssuer: 'https://repo-prod.prod.sagebase.org/auth/v1'
  OidcAuthorizationEndpoint: 'https://signin.synapse.org'
  OidcTokenEndpoint: 'https://qtg2zn2bbf.execute-api.us-east-1.amazonaws.com/token'
  OidcUserInfoEndpoint: 'https://repo-prod.prod.sagebase.org/auth/v1/oauth2/userinfo'
  OidcClientId: '100050'
hooks:
  before_launch:
    - !cmd "curl https://s3.amazonaws.com/bootstrap-awss3cloudformationbucket-19qromfd235z9/cfn-cr-alb-rule/master/cfn-cr-alb-rule.yaml --create-dirs -o templates/remote/cfn-cr-alb-rule.yaml"
```

Install the lambda using sceptre:
```shell script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/cfn-cr-alb-rule.yaml
```

## Author

[Tess Thyer](https://github.com/tthyer); Principal Data Engineer, Sage Bionetworks
