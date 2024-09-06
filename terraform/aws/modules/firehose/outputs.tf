# Kinesis Delivery Stream
output "kinesis_firehose_arn" {
  description = "The ARN of the Kinesis Firehose Stream"
  value       = var.create ? aws_kinesis_firehose_delivery_stream.this[0].arn : null
}

output "kinesis_firehose_name" {
  description = "The name of the Kinesis Firehose Stream"
  value       = var.create ? aws_kinesis_firehose_delivery_stream.this[0].name : null
}

output "kinesis_firehose_destination_id" {
  description = "The Destination id of the Kinesis Firehose Stream"
  value       = var.create ? aws_kinesis_firehose_delivery_stream.this[0].destination_id : null
}

output "kinesis_firehose_version_id" {
  description = "The Version id of the Kinesis Firehose Stream"
  value       = var.create ? aws_kinesis_firehose_delivery_stream.this[0].version_id : null
}

# CloudWatch Log Group
output "kinesis_firehose_cloudwatch_log_group_arn" {
  description = "The ARN of the created Cloudwatch Log Group"
  value       = try(aws_cloudwatch_log_group.log[0].arn, "")
}

output "kinesis_firehose_cloudwatch_log_group_name" {
  description = "The name of the created Cloudwatch Log Group"
  value       = try(aws_cloudwatch_log_group.log[0].name, "")
}

output "kinesis_firehose_cloudwatch_log_delivery_stream_arn" {
  description = "The ARN of the created Cloudwatch Log Group Stream to delivery"
  value       = try(aws_cloudwatch_log_stream.destination[0].arn, "")
}

output "kinesis_firehose_cloudwatch_log_delivery_stream_name" {
  description = "The name of the created Cloudwatch Log Group Stream to delivery"
  value       = try(aws_cloudwatch_log_stream.destination[0].name, "")
}

output "kinesis_firehose_cloudwatch_log_backup_stream_arn" {
  description = "The ARN of the created Cloudwatch Log Group Stream to backup"
  value       = try(aws_cloudwatch_log_stream.backup[0].arn, "")
}

output "kinesis_firehose_cloudwatch_log_backup_stream_name" {
  description = "The name of the created Cloudwatch Log Group Stream to backup"
  value       = try(aws_cloudwatch_log_stream.backup[0].name, "")
}

# IAM
output "kinesis_firehose_role_arn" {
  description = "The ARN of the IAM role created for Kinesis Firehose Stream"
  value       = try(aws_iam_role.firehose[0].arn, "")
}

output "s3_cross_account_bucket_policy" {
  description = "Bucket Policy to S3 Bucket Destination when the bucket belongs to another account"
  value       = try(data.aws_iam_policy_document.cross_account_s3[0].json, "")
}

output "opensearch_iam_service_linked_role_arn" {
  description = "The ARN of the Opensearch IAM Service linked role"
  value       = try(aws_iam_service_linked_role.opensearch[0].arn, "")
}

output "elasticsearch_cross_account_service_policy" {
  description = "Elasticsearch Service policy when the opensearch domain belongs to another account"
  value       = try(data.aws_iam_policy_document.cross_account_elasticsearch[0].json, "")
}

output "opensearch_cross_account_service_policy" {
  description = "Opensearch Service policy when the opensearch domain belongs to another account"
  value       = try(data.aws_iam_policy_document.cross_account_opensearch[0].json, "")
}

output "opensearchserverless_cross_account_service_policy" {
  description = "Opensearch Serverless Service policy when the opensearch domain belongs to another account"
  value       = try(data.aws_iam_policy_document.cross_account_opensearchserverless[0].json, "")
}


output "opensearchserverless_iam_service_linked_role_arn" {
  description = "The ARN of the Opensearch Serverless IAM Service linked role"
  value       = try(aws_iam_service_linked_role.opensearchserverless[0].arn, "")
}

output "application_role_arn" {
  description = "The ARN of the IAM role created for Kinesis Firehose Stream Source"
  value       = try(aws_iam_role.application[0].arn, "")
}

output "application_role_name" {
  description = "The Name of the IAM role created for Kinesis Firehose Stream Source Source"
  value       = try(aws_iam_role.application[0].name, "")
}

output "application_role_policy_arn" {
  description = "The ARN of the IAM policy created for Kinesis Firehose Stream Source"
  value       = try(aws_iam_policy.application[0].arn, "")
}

output "application_role_policy_name" {
  description = "The Name of the IAM policy created for Kinesis Firehose Stream Source Source"
  value       = try(aws_iam_policy.application[0].name, "")
}

# Security Group
output "firehose_security_group_id" {
  description = "Security Group ID associated to Firehose Stream. Only Supported for elasticsearch destination"
  value       = local.search_destination_vpc_create_firehose_sg ? aws_security_group.firehose[0].id : null
}

output "firehose_security_group_name" {
  description = "Security Group Name associated to Firehose Stream. Only Supported for elasticsearch destination"
  value       = local.search_destination_vpc_create_firehose_sg ? aws_security_group.firehose[0].name : null
}

output "destination_security_group_id" {
  description = "Security Group ID associated to destination"
  value       = local.vpc_create_destination_group ? aws_security_group.destination[0].id : null
}

output "destination_security_group_name" {
  description = "Security Group Name associated to destination"
  value       = local.vpc_create_destination_group ? aws_security_group.destination[0].name : null
}

output "firehose_security_group_rule_ids" {
  description = "Security Group Rules ID created in Firehose Stream Security group. Only Supported for elasticsearch destination"
  value       = local.search_destination_vpc_configure_existing_firehose_sg ? aws_security_group_rule.firehose[*].id : null
}

output "destination_security_group_rule_ids" {
  description = "Security Group Rules ID created in Destination Security group"
  value       = local.vpc_configure_destination_group ? { for key, value in var.vpc_security_group_destination_ids : value => aws_security_group_rule.destination[key].id } : null
}

output "firehose_cidr_blocks" {
  description = "Firehose stream cidr blocks to unblock on destination security group"
  value       = contains(["splunk", "redshift"], local.destination) ? local.firehose_cidr_blocks[local.destination][data.aws_region.current.name] : null
}
