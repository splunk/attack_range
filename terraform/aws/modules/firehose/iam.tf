locals {
  role_name                         = var.create && var.create_role ? coalesce(var.role_name, var.general.key_name, "*") : null
  application_role_name             = coalesce(var.application_role_name, "${var.general.key_name}-application-role", "*")
  create_application_role_policy    = var.create && var.create_application_role_policy
  add_backup_policies               = local.enable_s3_backup && var.s3_backup_use_existing_role
  add_kinesis_source_policy         = var.create && var.create_role && local.is_kinesis_source && var.kinesis_source_use_existing_role && var.source_use_existing_role
  add_msk_source_policy             = var.create && var.create_role && local.is_msk_source && var.source_use_existing_role
  add_lambda_policy                 = var.create && var.create_role && var.enable_lambda_transform
  add_s3_kms_policy                 = var.create && var.create_role && ((local.add_backup_policies && var.s3_backup_enable_encryption) || var.enable_s3_encryption)
  add_glue_policy                   = var.create && var.create_role && var.enable_data_format_conversion && var.data_format_conversion_glue_use_existing_role
  add_s3_policy                     = var.create && var.create_role
  add_cw_policy                     = var.create && var.create_role && ((local.add_backup_policies && var.s3_backup_enable_log) || var.enable_destination_log)
  add_elasticsearch_policy          = var.create && var.create_role && local.destination == "elasticsearch"
  add_opensearch_policy             = var.create && var.create_role && local.destination == "opensearch"
  add_opensearchserverless_policy   = var.create && var.create_role && local.destination == "opensearchserverless"
  add_vpc_policy                    = var.create && var.create_role && var.enable_vpc && var.vpc_use_existing_role && local.is_search_destination
  add_secretsmanager_policy         = var.create && var.create_role && var.enable_secrets_manager
  add_secretsmanager_decrypt_policy = local.add_secretsmanager_policy && var.secret_kms_key_arn != null
}

data "aws_iam_policy_document" "assume_role" {
  count = var.create && var.create_role ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"
      identifiers = compact([
        "firehose.amazonaws.com",
        var.destination == "redshift" ? "redshift.amazonaws.com" : "",
      ])
    }
    condition {
      test     = "StringEquals"
      values   = [data.aws_caller_identity.current.account_id]
      variable = "sts:ExternalId"
    }
  }
}

resource "aws_iam_role" "firehose" {
  count                 = var.create && var.create_role ? 1 : 0
  name                  = local.role_name
  description           = var.role_description
  path                  = var.role_path
  force_detach_policies = var.role_force_detach_policies
  permissions_boundary  = var.role_permissions_boundary
  assume_role_policy    = data.aws_iam_policy_document.assume_role[0].json
  tags                  = merge(var.tags, var.role_tags)
}

##################
# Kinesis Source
##################
data "aws_iam_policy_document" "kinesis" {
  count = local.add_kinesis_source_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:GetShardIterator",
      "kinesis:GetRecords",
      "kinesis:ListShards"
    ]
    resources = [var.kinesis_source_stream_arn]
  }

  dynamic "statement" {
    for_each = var.kinesis_source_is_encrypted ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "kms:Decrypt"
      ]
      resources = [var.kinesis_source_kms_arn]
      condition {
        test     = "StringEquals"
        values   = ["kinesis.${data.aws_region.current.name}.amazonaws.com"]
        variable = "kms:ViaService"
      }
      condition {
        test     = "StringLike"
        values   = [var.kinesis_source_stream_arn]
        variable = "kms:EncryptionContext:aws:kinesis:arn"
      }
    }
  }
}

resource "aws_iam_policy" "kinesis" {
  count  = local.add_kinesis_source_policy ? 1 : 0
  name   = "${local.role_name}-kinesis"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.kinesis[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "kinesis" {
  count      = local.add_kinesis_source_policy ? 1 : 0
  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.kinesis[0].arn
}

##################
# MSK Source
##################
data "aws_iam_policy_document" "msk" {
  count = local.add_msk_source_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "kafka:GetBootstrapBrokers",
      "kafka:DescribeCluster",
      "kafka:DescribeClusterV2",
      "kafka-cluster:Connect"
    ]
    resources = [var.msk_source_cluster_arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "kafka-cluster:DescribeTopic",
      "kafka-cluster:DescribeTopicDynamicConfiguration",
      "kafka-cluster:ReadData"
    ]
    resources = [
      "${var.msk_source_cluster_arn}/${var.msk_source_topic_name}"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "kafka-cluster:DescribeGroup"
    ]
    resources = [
      "${var.msk_source_cluster_arn}/*"
    ]
  }
}

resource "aws_iam_policy" "msk" {
  count  = local.is_msk_source ? 1 : 0
  name   = "${local.role_name}-msk"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.msk[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "msk" {
  count      = local.add_msk_source_policy ? 1 : 0
  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.msk[0].arn
}

##################
# Lambda
##################
data "aws_iam_policy_document" "lambda" {
  count = local.add_lambda_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
      "lambda:GetFunctionConfiguration"
    ]
    resources = [var.transform_lambda_arn]
  }
}

resource "aws_iam_policy" "lambda" {
  count  = local.add_lambda_policy ? 1 : 0
  name   = "${local.role_name}-lambda"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.lambda[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda" {
  count      = local.add_lambda_policy ? 1 : 0
  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.lambda[0].arn
}

##################
# KMS
##################
data "aws_iam_policy_document" "s3_kms" {
  count = local.add_s3_kms_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey"
    ]
    resources = distinct(compact([
      var.enable_s3_encryption ? var.s3_kms_key_arn : "",
      var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : ""
    ]))
    condition {
      test     = "StringEquals"
      values   = ["s3.${data.aws_region.current.name}.amazonaws.com"]
      variable = "kms:ViaService"
    }
    condition {
      test = "StringLike"
      values = distinct(compact([
        local.enable_s3_backup ? "${var.s3_backup_bucket_arn}/*" : "",
        var.enable_s3_encryption ? "${var.s3_backup_bucket_arn}/*" : ""
      ]))
      variable = "kms:EncryptionContext:aws:s3:arn"
    }
  }
}

resource "aws_iam_policy" "s3_kms" {
  count = local.add_s3_kms_policy ? 1 : 0

  name   = "${local.role_name}-s3-kms"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.s3_kms[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "s3_kms" {
  count = local.add_s3_kms_policy ? 1 : 0

  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.s3_kms[0].arn
}

##################
# Glue
##################
data "aws_iam_policy_document" "glue" {
  count = local.add_glue_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "glue:GetTable",
      "glue:GetTableVersion",
      "glue:GetTableVersions"
    ]
    resources = [
      "arn:aws:glue:${local.data_format_conversion_glue_region}:${local.data_format_conversion_glue_catalog_id}:catalog",
      "arn:aws:glue:${local.data_format_conversion_glue_region}:${local.data_format_conversion_glue_catalog_id}:database/${var.data_format_conversion_glue_database}",
      "arn:aws:glue:${local.data_format_conversion_glue_region}:${local.data_format_conversion_glue_catalog_id}:table/${var.data_format_conversion_glue_database}/${var.data_format_conversion_glue_table_name}"
    ]
  }
}

resource "aws_iam_policy" "glue" {
  count  = local.add_glue_policy ? 1 : 0
  name   = "${local.role_name}-glue"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.glue[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "glue" {
  count      = local.add_glue_policy ? 1 : 0
  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.glue[0].arn
}

##################
# S3
##################
data "aws_iam_policy_document" "s3" {
  count = local.add_s3_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = compact([
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
      !var.s3_own_bucket ? "s3:PutObjectAcl" : "",
    ])
    resources = distinct(compact([
      var.s3_bucket_arn != null ? var.s3_bucket_arn : "",
      var.s3_bucket_arn != null ? "${var.s3_bucket_arn}/*" : "",
      local.enable_s3_backup ? var.s3_backup_bucket_arn : "",
      local.enable_s3_backup ? "${var.s3_backup_bucket_arn}/*" : ""
    ]))
  }
}

resource "aws_iam_policy" "s3" {
  count  = local.add_s3_policy ? 1 : 0
  name   = "${local.role_name}-s3"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.s3[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "s3" {
  count      = local.add_s3_policy ? 1 : 0
  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.s3[0].arn
}

data "aws_iam_policy_document" "cross_account_s3" {
  count   = var.create && var.create_role && local.s3_destination && var.s3_cross_account ? 1 : 0
  version = "2012-10-17"
  statement {
    sid    = "Cross Account Access to ${data.aws_caller_identity.current.account_id} Account"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [local.firehose_role_arn]
    }

    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
      "s3:PutObjectAcl"
    ]

    resources = compact([
      var.s3_bucket_arn != null ? var.s3_bucket_arn : "",
      var.s3_bucket_arn != null ? "${var.s3_bucket_arn}/*" : "",
    ])
  }
}

##################
# Cloudwatch
##################
data "aws_iam_policy_document" "cw" {
  count = local.add_cw_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "logs:PutLogEvents"
    ]
    resources = distinct(compact([
      var.enable_destination_log ? "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:${local.destination_cw_log_group_name}:log-stream:${local.destination_cw_log_stream_name}" : "",
      var.s3_backup_enable_log ? "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:${local.s3_backup_cw_log_group_name}:log-stream:${local.s3_backup_cw_log_stream_name}" : ""
    ]))
  }
}

resource "aws_iam_policy" "cw" {
  count  = local.add_cw_policy ? 1 : 0
  name   = "${local.role_name}-cw"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.cw[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "cw" {
  count      = local.add_cw_policy ? 1 : 0
  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.cw[0].arn
}

##################
# Redshift
##################
resource "aws_redshift_cluster_iam_roles" "this" {
  count              = var.create && var.create_role && var.destination == "redshift" && var.associate_role_to_redshift_cluster ? 1 : 0
  cluster_identifier = var.redshift_cluster_identifier
  iam_role_arns      = [aws_iam_role.firehose[0].arn]
}

##################
# Elasticsearch
##################
data "aws_iam_policy_document" "elasticsearch" {
  count = local.add_elasticsearch_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "es:DescribeDomain",
      "es:DescribeDomains",
      "es:DescribeDomainConfig",
      "es:ESHttpPost",
      "es:ESHttpPut"
    ]
    resources = [
      var.elasticsearch_domain_arn,
      "${var.elasticsearch_domain_arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "es:ESHttpGet"
    ]
    resources = [
      "${var.elasticsearch_domain_arn}/_all/_settings",
      "${var.elasticsearch_domain_arn}/_cluster/stats",
      "${var.elasticsearch_domain_arn}/${var.elasticsearch_index_name}*/_mapping/${var.elasticsearch_type_name != null ? var.elasticsearch_type_name : "*"}",
      "${var.elasticsearch_domain_arn}/_nodes",
      "${var.elasticsearch_domain_arn}/_nodes/stats",
      "${var.elasticsearch_domain_arn}/_nodes/*/stats",
      "${var.elasticsearch_domain_arn}/_stats",
      "${var.elasticsearch_domain_arn}/${var.elasticsearch_index_name}*/_stats"
    ]
  }
}

resource "aws_iam_policy" "elasticsearch" {
  count = local.add_elasticsearch_policy ? 1 : 0

  name   = "${local.role_name}-elasticsearch"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.elasticsearch[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "elasticsearch" {
  count = local.add_elasticsearch_policy ? 1 : 0

  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.elasticsearch[0].arn
}

data "aws_iam_policy_document" "cross_account_elasticsearch" {
  count   = local.add_elasticsearch_policy && var.destination_cross_account ? 1 : 0
  version = "2012-10-17"
  statement {
    sid    = "Cross Account Access to ${data.aws_caller_identity.current.account_id} Account"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [local.firehose_role_arn]
    }

    actions = [
      "es:ESHttpGet"
    ]

    resources = [
      "${var.elasticsearch_domain_arn}/_all/_settings",
      "${var.elasticsearch_domain_arn}/_cluster/stats",
      "${var.elasticsearch_domain_arn}/${var.elasticsearch_index_name}*/_mapping/${var.elasticsearch_type_name != null ? var.elasticsearch_type_name : "*"}",
      "${var.elasticsearch_domain_arn}/_nodes",
      "${var.elasticsearch_domain_arn}/_nodes/stats",
      "${var.elasticsearch_domain_arn}/_nodes/*/stats",
      "${var.elasticsearch_domain_arn}/_stats",
      "${var.elasticsearch_domain_arn}/${var.elasticsearch_index_name}*/_stats"
    ]
  }
}

##################
# OpenSearch
##################
data "aws_iam_policy_document" "opensearch" {
  count = local.add_opensearch_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "es:DescribeDomain",
      "es:DescribeDomains",
      "es:DescribeDomainConfig",
      "es:ESHttpPost",
      "es:ESHttpPut"
    ]
    resources = [
      var.opensearch_domain_arn,
      "${var.opensearch_domain_arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "es:ESHttpGet"
    ]
    resources = [
      "${var.opensearch_domain_arn}/_all/_settings",
      "${var.opensearch_domain_arn}/_cluster/stats",
      "${var.opensearch_domain_arn}/${var.opensearch_index_name}*/_mapping/${var.opensearch_type_name != null ? var.opensearch_type_name : "*"}",
      "${var.opensearch_domain_arn}/_nodes",
      "${var.opensearch_domain_arn}/_nodes/stats",
      "${var.opensearch_domain_arn}/_nodes/*/stats",
      "${var.opensearch_domain_arn}/_stats",
      "${var.opensearch_domain_arn}/${var.opensearch_index_name}*/_stats"
    ]
  }
}

resource "aws_iam_policy" "opensearch" {
  count = local.add_opensearch_policy ? 1 : 0

  name   = "${local.role_name}-opensearch"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.opensearch[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "opensearch" {
  count = local.add_opensearch_policy ? 1 : 0

  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.opensearch[0].arn
}

data "aws_iam_policy_document" "cross_account_opensearch" {
  count   = local.add_opensearch_policy && var.destination_cross_account ? 1 : 0
  version = "2012-10-17"
  statement {
    sid    = "Cross Account Access to ${data.aws_caller_identity.current.account_id} Account"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [local.firehose_role_arn]
    }

    actions = [
      "es:ESHttpGet"
    ]

    resources = [
      "${var.opensearch_domain_arn}/_all/_settings",
      "${var.opensearch_domain_arn}/_cluster/stats",
      "${var.opensearch_domain_arn}/${var.opensearch_index_name}*/_mapping/${var.opensearch_type_name != null ? var.opensearch_type_name : "*"}",
      "${var.opensearch_domain_arn}/_nodes",
      "${var.opensearch_domain_arn}/_nodes/stats",
      "${var.opensearch_domain_arn}/_nodes/*/stats",
      "${var.opensearch_domain_arn}/_stats",
      "${var.opensearch_domain_arn}/${var.opensearch_index_name}*/_stats"
    ]
  }
}

resource "aws_iam_service_linked_role" "opensearch" {
  count            = contains(["elasticsearch", "opensearch"], local.destination) && var.enable_vpc && var.opensearch_vpc_create_service_linked_role ? 1 : 0
  aws_service_name = "opensearchservice.amazonaws.com"
  description      = "Allows Amazon OpenSearch to manage AWS resources for a domain on your behalf."
  tags             = merge(var.tags, var.role_tags)
}

##################
# Opensearch Serverless
##################
data "aws_iam_policy_document" "opensearchserverless" {
  count = local.add_opensearchserverless_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "aoss:APIAccessAll"
    ]
    resources = [
      var.opensearchserverless_collection_arn
    ]
  }
}

resource "aws_iam_policy" "opensearchserverless" {
  count = local.add_opensearchserverless_policy ? 1 : 0

  name   = "${local.role_name}-opensearchserverless"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.opensearchserverless[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "opensearchserverless" {
  count = local.add_opensearchserverless_policy ? 1 : 0

  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.opensearchserverless[0].arn
}

data "aws_iam_policy_document" "cross_account_opensearchserverless" {
  count   = local.add_opensearchserverless_policy && var.destination_cross_account ? 1 : 0
  version = "2012-10-17"
  statement {
    sid    = "Cross Account Access to ${data.aws_caller_identity.current.account_id} Account"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [local.firehose_role_arn]
    }

    actions = [
      "aoss:APIAccessAll"
    ]

    resources = [
      var.opensearchserverless_collection_arn
    ]
  }
}

resource "aws_iam_service_linked_role" "opensearchserverless" {
  count            = local.destination == "opensearchserverless" && var.opensearch_vpc_create_service_linked_role ? 1 : 0
  aws_service_name = "observability.aoss.amazonaws.com"
  description      = "Allows Amazon OpenSearch Serverless to manage AWS resources for a domain on your behalf."
  tags             = merge(var.tags, var.role_tags)
}

##################
# VPC
##################
data "aws_iam_policy_document" "vpc" {
  count = local.add_vpc_policy ? 1 : 0
  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeVpcs",
      "ec2:DescribeVpcAttribute",
      "ec2:DescribeSubnets",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeNetworkInterfaces",
      "ec2:CreateNetworkInterface",
      "ec2:CreateNetworkInterfacePermission",
      "ec2:DeleteNetworkInterface"
    ]
    resources = [
      "*"
    ]
  }
}

resource "aws_iam_policy" "vpc" {
  count = local.add_vpc_policy ? 1 : 0

  name   = "${local.role_name}-vpc"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.vpc[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "vpc" {
  count = local.add_vpc_policy ? 1 : 0

  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.vpc[0].arn
}

##################
# Application Role
##################
data "aws_iam_policy_document" "application_assume_role" {
  count = var.create_application_role ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = [var.application_role_service_principal]
    }
  }
}

resource "aws_iam_role" "application" {
  count                 = var.create_application_role ? 1 : 0
  name                  = local.application_role_name
  description           = var.application_role_description
  path                  = var.application_role_path
  force_detach_policies = var.application_role_force_detach_policies
  permissions_boundary  = var.application_role_permissions_boundary
  assume_role_policy    = data.aws_iam_policy_document.application_assume_role[0].json
  tags                  = merge(var.tags, var.application_role_tags)
}

data "aws_iam_policy_document" "application" {
  count = local.create_application_role_policy ? 1 : 0
  statement {
    effect    = "Allow"
    actions   = var.application_role_policy_actions
    resources = [aws_kinesis_firehose_delivery_stream.this[0].arn]
  }
}

resource "aws_iam_policy" "application" {
  count  = local.create_application_role_policy ? 1 : 0
  name   = "${local.application_role_name}-policy"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.application[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "application" {
  count      = (var.create_application_role || var.configure_existing_application_role) && local.create_application_role_policy ? 1 : 0
  role       = var.create_application_role ? aws_iam_role.application[0].name : var.application_role_name
  policy_arn = aws_iam_policy.application[0].arn
}

##################
# Secrets Manager
##################
data "aws_iam_policy_document" "secretsmanager" {
  count = local.add_secretsmanager_policy ? 1 : 0
  statement {
    sid    = "GetSecretValue"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      var.secret_arn
    ]
  }
}

resource "aws_iam_policy" "secretsmanager" {
  count = local.add_secretsmanager_policy ? 1 : 0

  name   = "${local.role_name}-secretsmanager"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.secretsmanager[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "secretsmanager" {
  count = local.add_secretsmanager_policy ? 1 : 0

  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.secretsmanager[0].arn
}

data "aws_iam_policy_document" "secretsmanager_cmk_encryption" {
  count = local.add_secretsmanager_decrypt_policy ? 1 : 0
  statement {
    sid    = "DecryptSecretWithKMSKey"
    effect = "Allow"
    actions = [
      "kms:Decrypt"
    ]
    resources = [
      var.secret_kms_key_arn
    ]
    condition {
      test     = "StringEquals"
      values   = ["secretsmanager.${data.aws_region.current.name}.amazonaws.com"]
      variable = "kms:ViaService"
    }
  }
}

resource "aws_iam_policy" "secretsmanager_cmk_encryption" {
  count = local.add_secretsmanager_decrypt_policy ? 1 : 0

  name   = "${local.role_name}-secretsmanager-cmk-encryption"
  path   = var.policy_path
  policy = data.aws_iam_policy_document.secretsmanager_cmk_encryption[0].json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "secretsmanager_cmk_encryption" {
  count = local.add_secretsmanager_decrypt_policy ? 1 : 0

  role       = aws_iam_role.firehose[0].name
  policy_arn = aws_iam_policy.secretsmanager_cmk_encryption[0].arn
}

# TODO: Support Cross Account Secret
# TODO: https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples_cross.html
# Generate Outputs to Secret Resource Policy??? On Cross account scenario
