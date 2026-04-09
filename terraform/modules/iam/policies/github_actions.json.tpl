{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformState",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
        "s3:ListBucket", "s3:GetBucketVersioning", "s3:GetEncryptionConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::${project_name}-tf-state",
        "arn:aws:s3:::${project_name}-tf-state/*"
      ]
    },
    {
      "Sid": "SSM",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter", "ssm:PutParameter", "ssm:DeleteParameter",
        "ssm:GetParameters", "ssm:ListTagsForResource",
        "ssm:AddTagsToResource", "ssm:RemoveTagsFromResource"
      ],
      "Resource": "arn:aws:ssm:${region}:${account_id}:parameter/${project_name}/*"
    },
    {
      "Sid": "SSMDescribe",
      "Effect": "Allow",
      "Action": ["ssm:DescribeParameters"],
      "Resource": "*"
    },
    {
      "Sid": "ECR",
      "Effect": "Allow",
      "Action": ["ecr:*"],
      "Resource": [
        "${ecr_repository_arn}",
        "${ecr_repository_bash_arn}"
      ]
    },
    {
      "Sid": "ECRAuth",
      "Effect": "Allow",
      "Action": ["ecr:GetAuthorizationToken"],
      "Resource": "*"
    },
    {
      "Sid": "ECS",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeClusters", "ecs:DescribeServices", "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition", "ecs:DeregisterTaskDefinition",
        "ecs:ListClusters", "ecs:ListServices", "ecs:ListTaskDefinitions",
        "ecs:CreateCluster", "ecs:CreateService", "ecs:UpdateService",
        "ecs:DeleteCluster", "ecs:DeleteService", "ecs:TagResource",
        "ecs:PutClusterCapacityProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRole",
      "Effect": "Allow",
      "Action": ["iam:PassRole", "iam:GetRole"],
      "Resource": "arn:aws:iam::${account_id}:role/${project_name}-*"
    },
    {
      "Sid": "IAMManage",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole", "iam:DeleteRole", "iam:GetRole", "iam:ListRolePolicies",
        "iam:GetRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
        "iam:ListAttachedRolePolicies", "iam:AttachRolePolicy", "iam:DetachRolePolicy",
        "iam:TagRole", "iam:UntagRole", "iam:ListInstanceProfilesForRole",
        "iam:CreateOpenIDConnectProvider", "iam:GetOpenIDConnectProvider",
        "iam:DeleteOpenIDConnectProvider", "iam:TagOpenIDConnectProvider",
        "iam:ListOpenIDConnectProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Lambda",
      "Effect": "Allow",
      "Action": ["lambda:*"],
      "Resource": "arn:aws:lambda:${region}:${account_id}:function:${project_name}-*"
    },
    {
      "Sid": "LambdaEventSourceMapping",
      "Effect": "Allow",
      "Action": [
        "lambda:ListEventSourceMappings", "lambda:GetEventSourceMapping",
        "lambda:CreateEventSourceMapping", "lambda:UpdateEventSourceMapping",
        "lambda:DeleteEventSourceMapping", "lambda:ListTags", "lambda:TagResource",
        "lambda:UntagResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SQS",
      "Effect": "Allow",
      "Action": ["sqs:*"],
      "Resource": "arn:aws:sqs:${region}:${account_id}:${project_name}-*"
    },
    {
      "Sid": "S3Workspaces",
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["${s3_bucket_arn}", "${s3_bucket_arn}/*"]
    },
    {
      "Sid": "APIGateway",
      "Effect": "Allow",
      "Action": ["apigateway:*"],
      "Resource": "arn:aws:apigateway:${region}::/*"
    },
    {
      "Sid": "CloudWatch",
      "Effect": "Allow",
      "Action": ["logs:*", "cloudwatch:*", "application-autoscaling:*"],
      "Resource": "*"
    },
    {
      "Sid": "VPC",
      "Effect": "Allow",
      "Action": ["ec2:*"],
      "Resource": "*"
    }
  ]
}
