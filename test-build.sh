set -ex

sam build
sam package --profile admincentral-cfn --template-file .aws-sam/build/template.yaml \
  --s3-bucket essentials-awss3lambdaartifactsbucket-x29ftznj6pqw \
  --output-template-file .aws-sam/build/cfn-cr-alb-rule.yaml
aws --profile admincentral-cfn s3 cp .aws-sam/build/cfn-cr-alb-rule.yaml \
  s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/cfn-cr-alb-rule/master/

set +ex
