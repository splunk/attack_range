



resource "aws_lambda_function" "example" {
   count = var.cloud_attack_range ? 1 : 0
   function_name = "notes_application_${var.key_name}"

   # The bucket name as created earlier with "aws s3api create-bucket"
   s3_bucket = "attack-range-appbinaries"
   s3_key    = "serverless-application/v1.0.0/serverless-flask.zip"

   # "main" is the filename within the zip file (main.js) and "handler"
   # is the name of the property under which the handler function was
   # exported in that file.
   handler = "wsgi_handler.handler"
   runtime = "python3.7"

   role = aws_iam_role.lambda_exec[0].arn
 }

 # IAM role which dictates what other AWS services the Lambda function
 # may access.
resource "aws_iam_role" "lambda_exec" {
   count = var.cloud_attack_range ? 1 : 0
   name = "iam_roles_notes_app_${var.key_name}"

   assume_role_policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "lambda.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
EOF

}

# resource "aws_cloudwatch_log_group" "attack_range" {
#   count             = var.cloud_attack_range ? 1 : 0
#   name              = "/aws/lambda/notes_application_${var.key_name}"
#   retention_in_days = 7
# }

# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
resource "aws_iam_policy" "lambda_logging" {
  count       = var.cloud_attack_range ? 1 : 0
  name        = "lambda_logging_${var.key_name}"
  path        = "/"
  description = "IAM policy for logging from a lambda"

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:GetLogRecord",
                "logs:DescribeLogGroups"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:Describe*",
                "logs:FilterLogEvents",
                "logs:GetLogEvents"
            ],
            "Resource": "arn:aws:logs:*:log-group:/aws/lambda/notes_application_attack-range-key-pair:*"
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  count      = var.cloud_attack_range ? 1 : 0
  role       = "${aws_iam_role.lambda_exec[0].name}"
  policy_arn = "${aws_iam_policy.lambda_logging[0].arn}"
}


## REST API Gateway

resource "aws_cloudwatch_log_group" "rest_api" {
  count             = var.cloud_attack_range ? 1 : 0
  name              = "API-Gateway-Execution-Logs_${aws_api_gateway_rest_api.example[0].id}/prod"
  retention_in_days = 7
}

resource "aws_api_gateway_method_settings" "s" {
  count       = var.cloud_attack_range ? 1 : 0
  rest_api_id = "${aws_api_gateway_rest_api.example[0].id}"
  stage_name  = "${aws_api_gateway_stage.prod[0].stage_name}"
  method_path = "*/*"

  settings {
    metrics_enabled = true
    logging_level   = "INFO"
  }
}


resource "aws_api_gateway_rest_api" "example" {
  count       = var.cloud_attack_range ? 1 : 0
  name        = "api_gateway_${var.key_name}"
  description = "Attack Range Rest API Notes Application"
}


resource "aws_api_gateway_stage" "prod" {
  count          = var.cloud_attack_range ? 1 : 0
  depends_on    = ["aws_cloudwatch_log_group.rest_api[0]"]
  stage_name    = "prod"
  rest_api_id   = aws_api_gateway_rest_api.example[0].id
  deployment_id = aws_api_gateway_deployment.example[0].id
}

resource "aws_api_gateway_resource" "proxy" {
  count       = var.cloud_attack_range ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.example[0].id
  parent_id   = aws_api_gateway_rest_api.example[0].root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy" {
  count         = var.cloud_attack_range ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.example[0].id
  resource_id   = aws_api_gateway_resource.proxy[0].id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
   count       = var.cloud_attack_range ? 1 : 0
   rest_api_id = aws_api_gateway_rest_api.example[0].id
   resource_id = aws_api_gateway_method.proxy[0].resource_id
   http_method = aws_api_gateway_method.proxy[0].http_method

   integration_http_method = "POST"
   type                    = "AWS_PROXY"
   uri                     = aws_lambda_function.example[0].invoke_arn
 }

 resource "aws_api_gateway_method" "proxy_root" {
   count         = var.cloud_attack_range ? 1 : 0
   rest_api_id   = aws_api_gateway_rest_api.example[0].id
   resource_id   = aws_api_gateway_rest_api.example[0].root_resource_id
   http_method   = "ANY"
   authorization = "NONE"
 }

 resource "aws_api_gateway_integration" "lambda_root" {
   count       = var.cloud_attack_range ? 1 : 0
   rest_api_id = aws_api_gateway_rest_api.example[0].id
   resource_id = aws_api_gateway_method.proxy_root[0].resource_id
   http_method = aws_api_gateway_method.proxy_root[0].http_method

   integration_http_method = "POST"
   type                    = "AWS_PROXY"
   uri                     = aws_lambda_function.example[0].invoke_arn
 }

 resource "aws_api_gateway_deployment" "example" {
   count       = var.cloud_attack_range ? 1 : 0
   depends_on = [
     aws_api_gateway_integration.lambda[0],
     aws_api_gateway_integration.lambda_root[0],
   ]

   rest_api_id = aws_api_gateway_rest_api.example[0].id
 }

 resource "aws_lambda_permission" "apigw" {
  count       = var.cloud_attack_range ? 1 : 0
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.example[0].function_name
  principal     = "apigateway.amazonaws.com"

  # The "/*/*" portion grants access from any method on any resource
  # within the API Gateway REST API.
  source_arn = "${aws_api_gateway_rest_api.example[0].execution_arn}/*/*"
}


## Amazon RDS database

data "aws_iam_policy_document" "enhanced_monitoring" {
  count = var.cloud_attack_range ? 1 : 0
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "enhanced_monitoring" {
  count              = var.cloud_attack_range ? 1 : 0
  name               = "EnhancedMonitoringARN_${var.key_name}"
  assume_role_policy = data.aws_iam_policy_document.enhanced_monitoring[0].json
}

resource "aws_iam_role_policy_attachment" "enhanced_monitoring" {
  count      = var.cloud_attack_range ? 1 : 0
  role       = aws_iam_role.enhanced_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_subnet" "subnet_db1" {
  count                   = var.cloud_attack_range ? 1 : 0
  vpc_id                  = var.vpc_id
  cidr_block              = var.subnet_db1
  availability_zone       = var.availability_zone_db1
}

resource "aws_subnet" "subnet_db2" {
  count                   = var.cloud_attack_range ? 1 : 0
  vpc_id                  = var.vpc_id
  cidr_block              = var.subnet_db2
  availability_zone       = var.availability_zone_db2
}

resource "aws_db_subnet_group" "db_subnet_group" {
  count      = var.cloud_attack_range ? 1 : 0
  name       = "db subnet group"
  subnet_ids = [aws_subnet.subnet_db1[0].id, aws_subnet.subnet_db2[0].id]
}

resource "aws_security_group" "sg_subnet1" {
  count = var.cloud_attack_range ? 1 : 0
  name = "sg_subnet1"
  vpc_id = var.vpc_id

  # Only postgres in
  ingress {
    from_port = 3306
    to_port = 3306
    protocol = "tcp"
    cidr_blocks = concat(var.ip_whitelist, [var.subnet_db1])
  }

  # Allow all outbound traffic.
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "sg_subnet2" {
  count = var.cloud_attack_range ? 1 : 0
  name = "sg_subnet2"
  vpc_id = var.vpc_id

  # Only postgres in
  ingress {
    from_port = 3306
    to_port = 3306
    protocol = "tcp"
    cidr_blocks = concat(var.ip_whitelist, [var.subnet_db2])
  }

  # Allow all outbound traffic.
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "db_attack_range" {
  count                = var.cloud_attack_range ? 1 : 0
  availability_zone    = var.availability_zone_db1
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "mysql"
  engine_version       = "5.7"
  instance_class       = "db.t2.micro"
  name                 = "notedb"
  identifier           = "db-${var.key_name}"
  username             = var.db_user
  password             = var.db_password
  parameter_group_name = "default.mysql5.7"
  vpc_security_group_ids = [aws_security_group.sg_subnet1[0].id, aws_security_group.sg_subnet2[0].id]
  db_subnet_group_name = aws_db_subnet_group.db_subnet_group[0].id
  skip_final_snapshot  = "true"
  publicly_accessible  = "true"
  monitoring_interval  = 10
  monitoring_role_arn  = aws_iam_role.enhanced_monitoring[0].arn
}
