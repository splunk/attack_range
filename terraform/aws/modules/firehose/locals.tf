locals {
  firehose_role_arn           = var.create && var.create_role ? aws_iam_role.firehose[0].arn : var.firehose_role
  cw_log_group_name           = "/aws/kinesisfirehose/${var.general.key_name}"
  cw_log_delivery_stream_name = "DestinationDelivery"
  cw_log_backup_stream_name   = "BackupDelivery"
  is_kinesis_source           = var.input_source == "kinesis" ? true : false
  is_waf_source               = var.input_source == "waf" ? true : false
  is_msk_source               = var.input_source == "msk" ? true : false
  destinations = {
    s3 : "extended_s3",
    extended_s3 : "extended_s3",
    redshift : "redshift",
    elasticsearch : "elasticsearch",
    opensearch : "opensearch",
    opensearchserverless : "opensearchserverless",
    splunk : "splunk",
    http_endpoint : "http_endpoint",
    datadog : "http_endpoint",
    coralogix : "http_endpoint",
    newrelic : "http_endpoint",
    dynatrace : "http_endpoint",
    honeycomb : "http_endpoint",
    logicmonitor : "http_endpoint",
    mongodb : "http_endpoint",
    sumologic : "http_endpoint",
    snowflake : "snowflake"
  }
  destination           = local.destinations[var.destination]
  s3_destination        = local.destination == "extended_s3" ? true : false
  is_search_destination = contains(["elasticsearch", "opensearch", "opensearchserverless"], local.destination) ? true : false

  # Data Transformation
  enable_processing = var.enable_lambda_transform || var.enable_dynamic_partitioning || var.enable_cloudwatch_logs_decompression || var.dynamic_partition_append_delimiter_to_record || var.append_delimiter_to_record
  lambda_processor_parameters = [
    {
      name  = "LambdaArn"
      value = var.transform_lambda_arn
    },
    var.transform_lambda_buffer_size != null ?
    {
      name  = "BufferSizeInMBs"
      value = var.transform_lambda_buffer_size
    } : null,
    var.transform_lambda_buffer_interval != null ?
    {
      name  = "BufferIntervalInSeconds"
      value = var.transform_lambda_buffer_interval
    } : null,
    var.transform_lambda_number_retries != null ?
    {
      name  = "NumberOfRetries"
      value = var.transform_lambda_number_retries
    } : null,
    var.transform_lambda_role_arn != null ?
    {
      name  = "RoleArn"
      value = var.transform_lambda_role_arn
    } : null,
  ]
  lambda_processor = var.enable_lambda_transform ? {
    type       = "Lambda"
    parameters = [for parameter in local.lambda_processor_parameters : parameter if parameter != null]
  } : null
  metadata_extractor_processor = var.enable_dynamic_partitioning && var.dynamic_partition_metadata_extractor_query != null ? {
    type = "MetadataExtraction"
    parameters = [
      {
        name  = "JsonParsingEngine"
        value = "JQ-1.6"
      },
      {
        name  = "MetadataExtractionQuery"
        value = var.dynamic_partition_metadata_extractor_query
      },
    ]
  } : null
  append_delimiter_processor = var.dynamic_partition_append_delimiter_to_record || var.append_delimiter_to_record ? {
    type       = "AppendDelimiterToRecord"
    parameters = []
  } : null
  record_deaggregation_processor_json = {
    type = "RecordDeAggregation"
    parameters = [
      {
        name  = "SubRecordType"
        value = var.dynamic_partition_record_deaggregation_type
      },
    ]
  }
  record_deaggregation_processor_delimiter = {
    type = "RecordDeAggregation"
    parameters = [
      {
        name  = "SubRecordType"
        value = var.dynamic_partition_record_deaggregation_type
      },
      {
        name  = "Delimiter"
        value = var.dynamic_partition_record_deaggregation_delimiter
      },
    ]
  }
  record_deaggregation_processor = (var.enable_dynamic_partitioning && var.dynamic_partition_enable_record_deaggregation ?
    (var.dynamic_partition_record_deaggregation_type == "JSON" ? local.record_deaggregation_processor_json : local.record_deaggregation_processor_delimiter)
  : null)
  cloudwatch_logs_decompression_processor = var.enable_cloudwatch_logs_decompression ? {
    type = "Decompression"
    parameters = [
      {
        name  = "CompressionFormat"
        value = "GZIP"
      }
    ]
  } : null
  cloudwatch_logs_data_message_extraction_processor = var.enable_cloudwatch_logs_decompression && var.enable_cloudwatch_logs_data_message_extraction ? {
    type = "CloudWatchLogProcessing"
    parameters = [
      {
        name  = "DataMessageExtraction"
        value = tostring(var.enable_cloudwatch_logs_data_message_extraction)
      },
    ]
  } : null
  processors = [for each in [
    local.lambda_processor,
    local.metadata_extractor_processor,
    local.append_delimiter_processor,
    local.record_deaggregation_processor,
    local.cloudwatch_logs_decompression_processor,
    local.cloudwatch_logs_data_message_extraction_processor
  ] : each if local.enable_processing && each != null]

  # Data Format conversion
  data_format_conversion_glue_catalog_id = (var.enable_data_format_conversion ?
    (var.data_format_conversion_glue_catalog_id != null ? var.data_format_conversion_glue_catalog_id : data.aws_caller_identity.current.account_id)
  : null)

  data_format_conversion_glue_region = (var.enable_data_format_conversion ?
    (var.data_format_conversion_glue_region != null ? var.data_format_conversion_glue_region : data.aws_region.current.name)
  : null)

  data_format_conversion_glue_role = (var.enable_data_format_conversion ? (
    var.data_format_conversion_glue_use_existing_role ? local.firehose_role_arn : var.data_format_conversion_glue_role_arn
  ) : null)

  # S3 Backup
  use_backup_vars_in_s3_configuration = contains(["elasticsearch", "opensearch", "opensearchserverless", "splunk", "http_endpoint", "snowflake"], local.destination) ? true : false
  s3_backup                           = var.enable_s3_backup ? "Enabled" : "Disabled"
  enable_s3_backup                    = var.enable_s3_backup || local.use_backup_vars_in_s3_configuration
  s3_backup_role_arn = (local.enable_s3_backup ? (
    var.s3_backup_use_existing_role ? local.firehose_role_arn : var.s3_backup_role_arn
  ) : null)
  s3_backup_cw_log_group_name  = var.create_destination_cw_log_group ? local.cw_log_group_name : var.s3_backup_log_group_name
  s3_backup_cw_log_stream_name = var.create_destination_cw_log_group ? local.cw_log_backup_stream_name : var.s3_backup_log_stream_name
  backup_modes = {
    elasticsearch : {
      FailedOnly : "FailedDocumentsOnly",
      All : "AllDocuments"
    }
    opensearch : {
      FailedOnly : "FailedDocumentsOnly",
      All : "AllDocuments"
    }
    opensearchserverless : {
      FailedOnly : "FailedDocumentsOnly",
      All : "AllDocuments"
    }
    splunk : {
      FailedOnly : "FailedEventsOnly",
      All : "AllEvents"
    }
    http_endpoint : {
      FailedOnly : "FailedDataOnly",
      All : "AllData"
    }
    snowflake : {
      FailedOnly : "FailedDataOnly",
      All : "AllData"
    }
  }
  s3_backup_mode = local.use_backup_vars_in_s3_configuration ? local.backup_modes[local.destination][var.s3_backup_mode] : null

  # Common Source Variables
  source_role = (local.is_kinesis_source || local.is_msk_source ? (
    var.source_use_existing_role ? local.firehose_role_arn : var.source_role_arn
  ) : null)

  # Kinesis source Stream
  kinesis_source_stream_role = (local.is_kinesis_source ? ( # TODO: Deprecated. Remove Next Major Version
    var.kinesis_source_use_existing_role ? local.firehose_role_arn : var.kinesis_source_role_arn
  ) : null)

  # Destination Log
  destination_cw_log_group_name  = var.create_destination_cw_log_group ? local.cw_log_group_name : var.destination_log_group_name
  destination_cw_log_stream_name = var.create_destination_cw_log_group ? local.cw_log_delivery_stream_name : var.destination_log_stream_name

  # Cloudwatch
  create_destination_logs = var.create && var.enable_destination_log && var.create_destination_cw_log_group
  create_backup_logs      = var.create && var.enable_s3_backup && var.s3_backup_enable_log && var.s3_backup_create_cw_log_group

  # VPC Config
  vpc_role_arn = (var.enable_vpc ? (
    var.vpc_use_existing_role ? local.firehose_role_arn : var.vpc_role_arn
  ) : null)

  search_destination_vpc_create_firehose_sg                    = local.is_search_destination && var.vpc_create_security_group
  search_destination_vpc_sgs                                   = local.search_destination_vpc_create_firehose_sg ? [aws_security_group.firehose[0].id] : var.vpc_security_group_firehose_ids
  search_destination_vpc_configure_existing_firehose_sg        = local.is_search_destination && var.enable_vpc && var.vpc_security_group_firehose_configure_existing && !local.search_destination_vpc_create_firehose_sg
  search_destination_vpc_create_destination_group              = local.is_search_destination && var.vpc_create_destination_security_group && !var.vpc_security_group_same_as_destination
  search_destination_vpc_firehose_sgs                          = local.search_destination_vpc_create_firehose_sg ? [aws_security_group.firehose[0].id] : var.vpc_security_group_firehose_ids
  search_destination_vpc_destination_sgs                       = local.search_destination_vpc_create_destination_group ? [aws_security_group.destination[0].id] : var.vpc_security_group_destination_ids
  not_search_destination_vpc_create_destination_group          = contains(["splunk", "redshift"], local.destination) && var.vpc_create_destination_security_group
  vpc_create_destination_group                                 = local.search_destination_vpc_create_destination_group || local.not_search_destination_vpc_create_destination_group
  search_destination_vpc_configure_existing_destination_sg     = local.is_search_destination && var.enable_vpc && var.vpc_security_group_destination_configure_existing && !local.search_destination_vpc_create_destination_group && !var.vpc_security_group_same_as_destination
  not_search_destination_vpc_configure_existing_destination_sg = contains(["splunk", "redshift"], local.destination) && var.vpc_security_group_destination_configure_existing
  vpc_configure_destination_group                              = local.search_destination_vpc_configure_existing_destination_sg || local.not_search_destination_vpc_configure_existing_destination_sg

  http_endpoint_url = {
    http_endpoint : var.http_endpoint_url
    datadog : local.datadog_endpoint_url[var.datadog_endpoint_type]
    coralogix : local.coralogix_endpoint_url[var.coralogix_endpoint_location]
    newrelic : local.newrelic_endpoint_url[var.newrelic_endpoint_type]
    dynatrace : local.dynatrace_endpoint_url[var.dynatrace_endpoint_location]
    honeycomb : "${coalesce(var.honeycomb_api_host, "n/a")}/1/kinesis_events/${coalesce(var.honeycomb_dataset_name, "n/a")}"
    logicmonitor : "https://${coalesce(var.logicmonitor_account, "n/a")}.logicmonitor.com"
    mongodb : coalesce(var.mongodb_realm_webhook_url, "n/a")
    sumologic : "https://${coalesce(var.sumologic_deployment_name, "n/a")}.sumologic.net/receiver/v1/kinesis/${coalesce(var.sumologic_data_type, "n/a")}/${coalesce(var.http_endpoint_access_key, "n/a")}"
  }

  http_endpoint_name = {
    http_endpoint : var.http_endpoint_name
    datadog : "Datadog"
    coralogix : "Coralogix"
    newrelic : "New Relic"
    dynatrace : "Dynatrace"
    honeycomb : "Honeycomb"
    logicmonitor : "LogicMonitor"
    mongodb : "MongoDB Cloud"
    sumologic : "Sumo Logic"
  }

  http_endpoint_destinations_parameters = {
    coralogix : local.coralogix_parameters
    dynatrace : local.dynatrace_parameters
  }

  # DataDog
  datadog_endpoint_url = {
    logs_us : "https://aws-kinesis-http-intake.logs.datadoghq.com/v1/input"
    logs_eu : "https://aws-kinesis-http-intake.logs.datadoghq.eu/v1/input"
    logs_gov : "https://aws-kinesis-http-intake.logs.ddog-gov.com/v1/input"
    metrics_us : "https://awsmetrics-intake.datadoghq.com/v1/input"
    metrics_eu : "https://awsmetrics-intake.datadoghq.eu/v1/input"
  }

  # New Relic
  newrelic_endpoint_url = {
    logs_us : "https://aws-api.newrelic.om/firehose/v1"
    logs_eu : "https://aws-api.eu.newrelic.com/firehose/v1"
    metrics_us : "https://aws-api.newrelic.com/cloudwatch-metrics/v1"
    metrics_eu : "https://aws-api.eu01.nr-data.net/cloudwatch-metrics/v1"
  }

  # Dynatrace
  dynatrace_endpoint_url = {
    us : "https://us.aws.cloud.dynatrace.com"
    eu : "https://eu.aws.cloud.dynatrace.com"
    global : "https://aws.cloud.dynatrace.com"
  }

  dynatrace_parameters = concat(
    var.destination == "dynatrace" ? [{
      name  = "dt-url"
      value = var.dynatrace_api_url
    }] : [],
  )

  # Coralogix
  coralogix_endpoint_url = {
    us : "https://firehose-ingress.coralogix.us/firehose"
    singapore : "https://firehose-ingress.coralogixsg.com/firehose"
    ireland : "https://firehose-ingress.coralogix.com/firehose"
    india : "https://firehose-ingress.coralogix.in/firehose"
    stockholm : "https://firehose-ingress.eu2.coralogix.com/firehose"
  }

  coralogix_parameters = concat(
    var.coralogix_parameter_application_name != null ? [{
      name  = "applicationName"
      value = var.coralogix_parameter_application_name
    }] : [],
    var.coralogix_parameter_subsystem_name != null ? [{
      name  = "subsystemName"
      value = var.coralogix_parameter_subsystem_name
    }] : [],
    var.coralogix_parameter_use_dynamic_values ? [{
      name  = "dynamicMetadata"
      value = var.coralogix_parameter_use_dynamic_values
    }] : []
  )

  # Networking
  firehose_cidr_blocks = {
    redshift : {
      us-east-2 : ["13.58.135.96/27"],
      us-east-1 : ["52.70.63.192/27"],
      us-west-1 : ["13.57.135.192/27"],
      us-west-2 : ["52.89.255.224/27"],
      us-gov-east-1 : ["18.253.138.96/27"],
      us-gov-west-1 : ["52.61.204.160/27"],
      ap-east-1 : ["18.162.221.32/27"],
      ap-south-1 : ["13.232.67.32/27"],
      ap-northeast-2 : ["13.209.1.64/27"],
      ap-southeast-1 : ["13.228.64.192/27"],
      ap-southeast-2 : ["13.210.67.224/27"],
      ap-northeast-1 : ["13.113.196.224/27"],
      ca-central-1 : ["35.183.92.128/27"],
      af-south-1 : ["13.244.121.224/27"],
      ap-southeast-3 : ["108.136.221.64/27"],
      ap-northeast-3 : ["13.208.177.192/27"],
      eu-central-1 : ["35.158.127.160/27"],
      eu-west-1 : ["52.19.239.192/27"],
      eu-west-2 : ["18.130.1.96/27"],
      eu-south-1 : ["15.161.135.128/27"],
      eu-west-3 : ["35.180.1.96/27"],
      eu-north-1 : ["13.53.63.224/27"],
      me-south-1 : ["15.185.91.0/27"],
      sa-east-1 : ["18.228.1.128/27"],
      cn-north-1 : ["52.81.151.32/27"],
      cn-northwest-1 : ["161.189.23.64/27"],
    },
    splunk : {
      us-east-2 : ["18.216.68.160/27", "18.216.170.64/27", "18.216.170.96/27"],
      us-east-1 : ["34.238.188.128/26", "34.238.188.192/26", "34.238.195.0/26"],
      us-west-1 : ["13.57.180.0/26"],
      us-west-2 : ["34.216.24.32/27", "34.216.24.192/27", "34.216.24.224/27"],
      us-gov-east-1 : ["18.253.138.192/26"],
      us-gov-west-1 : ["52.61.204.192/26"],
      ap-east-1 : ["18.162.221.64/26"],
      ap-south-1 : ["13.232.67.64/26"],
      ap-northeast-2 : ["13.209.71.0/26"],
      ap-southeast-1 : ["13.229.187.128/26"],
      ap-southeast-2 : ["13.211.12.0/26"],
      ap-northeast-1 : ["13.230.21.0/27", "13.230.21.32/27"],
      ca-central-1 : ["35.183.92.64/26"],
      af-south-1 : ["13.244.165.128/26"],
      ap-southeast-3 : ["108.136.221.128/26"],
      ap-northeast-3 : ["13.208.217.0/26"],
      eu-central-1 : ["18.194.95.192/27", "18.194.95.224/27", "18.195.48.0/27"],
      eu-west-1 : ["34.241.197.32/27", "34.241.197.64/27", "34.241.197.96/27"],
      eu-west-2 : ["18.130.91.0/26"],
      eu-south-1 : ["15.161.135.192/26"],
      eu-west-3 : ["35.180.112.0/26"],
      eu-north-1 : ["13.53.191.0/26"],
      me-south-1 : ["15.185.91.64/26"],
      sa-east-1 : ["18.228.1.192/26"],
      cn-north-1 : ["52.81.151.64/26"],
      cn-northwest-1 : ["161.189.23.128/26"],
    }
  }
}
