data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_subnet" "subnet" {
  count = local.search_destination_vpc_create_firehose_sg && var.enable_vpc ? 1 : 0
  id    = var.vpc_subnet_ids[0]
}

resource "aws_kinesis_firehose_delivery_stream" "this" {
  count       = var.create ? 1 : 0
  name        = "aws-waf-logs-${var.general.key_name}"
  destination = local.destination

  dynamic "kinesis_source_configuration" {
    for_each = local.is_kinesis_source ? [1] : []
    content {
      kinesis_stream_arn = var.kinesis_source_stream_arn
      role_arn           = var.kinesis_source_use_existing_role ? local.source_role : local.kinesis_source_stream_role # TODO: Next Major version, role should be equals to local.source_role
    }
  }

  dynamic "msk_source_configuration" {
    for_each = local.is_msk_source ? [1] : []
    content {
      authentication_configuration {
        connectivity = var.msk_source_connectivity_type
        role_arn     = local.source_role
      }
      msk_cluster_arn = var.msk_source_cluster_arn
      topic_name      = var.msk_source_topic_name
    }
  }

  dynamic "server_side_encryption" {
    for_each = !local.is_kinesis_source && var.enable_sse ? [1] : []
    content {
      enabled  = var.enable_sse
      key_arn  = var.sse_kms_key_arn
      key_type = var.sse_kms_key_type
    }
  }

  dynamic "extended_s3_configuration" {
    for_each = local.s3_destination ? [1] : []
    content {
      role_arn            = local.firehose_role_arn
      bucket_arn          = var.s3_bucket_arn
      prefix              = var.s3_prefix
      error_output_prefix = var.s3_error_output_prefix
      buffering_size      = var.buffering_size
      buffering_interval  = var.buffering_interval
      s3_backup_mode      = local.s3_backup
      kms_key_arn         = var.enable_s3_encryption ? var.s3_kms_key_arn : null
      compression_format  = var.s3_compression_format

      dynamic "dynamic_partitioning_configuration" {
        for_each = var.enable_dynamic_partitioning ? [1] : []
        content {
          enabled        = var.enable_dynamic_partitioning
          retry_duration = var.dynamic_partitioning_retry_duration
        }
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "data_format_conversion_configuration" {
        for_each = var.enable_data_format_conversion ? [1] : []
        content {
          input_format_configuration {
            deserializer {
              dynamic "open_x_json_ser_de" {
                for_each = var.data_format_conversion_input_format == "OpenX" ? [1] : []
                content {
                  case_insensitive                         = var.data_format_conversion_openx_case_insensitive
                  convert_dots_in_json_keys_to_underscores = var.data_format_conversion_openx_convert_dots_to_underscores
                  column_to_json_key_mappings              = var.data_format_conversion_openx_column_to_json_key_mappings
                }
              }
              dynamic "hive_json_ser_de" {
                for_each = var.data_format_conversion_input_format == "HIVE" ? [1] : []
                content {
                  timestamp_formats = var.data_format_conversion_hive_timestamps
                }
              }
            }
          }

          output_format_configuration {
            serializer {
              dynamic "parquet_ser_de" {
                for_each = var.data_format_conversion_output_format == "PARQUET" ? [1] : []
                content {
                  block_size_bytes              = var.data_format_conversion_block_size
                  compression                   = var.data_format_conversion_parquet_compression
                  enable_dictionary_compression = var.data_format_conversion_parquet_dict_compression
                  max_padding_bytes             = var.data_format_conversion_parquet_max_padding
                  page_size_bytes               = var.data_format_conversion_parquet_page_size
                  writer_version                = var.data_format_conversion_parquet_writer_version
                }
              }
              dynamic "orc_ser_de" {
                for_each = var.data_format_conversion_output_format == "ORC" ? [1] : []
                content {
                  block_size_bytes                        = var.data_format_conversion_block_size
                  compression                             = var.data_format_conversion_orc_compression
                  format_version                          = var.data_format_conversion_orc_format_version
                  enable_padding                          = var.data_format_conversion_orc_enable_padding
                  padding_tolerance                       = var.data_format_conversion_orc_padding_tolerance
                  dictionary_key_threshold                = var.data_format_conversion_orc_dict_key_threshold
                  bloom_filter_columns                    = var.data_format_conversion_orc_bloom_filter_columns
                  bloom_filter_false_positive_probability = var.data_format_conversion_orc_bloom_filter_false_positive_probability
                  row_index_stride                        = var.data_format_conversion_orc_row_index_stripe
                  stripe_size_bytes                       = var.data_format_conversion_orc_stripe_size
                }
              }
            }
          }

          schema_configuration {
            database_name = var.data_format_conversion_glue_database
            role_arn      = local.data_format_conversion_glue_role
            table_name    = var.data_format_conversion_glue_table_name
            catalog_id    = local.data_format_conversion_glue_catalog_id
            region        = local.data_format_conversion_glue_region
            version_id    = var.data_format_conversion_glue_version_id
          }
        }
      }

      dynamic "s3_backup_configuration" {
        for_each = var.enable_s3_backup ? [1] : []
        content {
          bucket_arn          = var.s3_backup_bucket_arn
          role_arn            = local.s3_backup_role_arn
          prefix              = var.s3_backup_prefix
          buffering_size      = var.s3_backup_buffering_size
          buffering_interval  = var.s3_backup_buffering_interval
          compression_format  = var.s3_backup_compression
          error_output_prefix = var.s3_backup_error_output_prefix
          kms_key_arn         = var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null
          cloudwatch_logging_options {
            enabled         = var.s3_backup_enable_log
            log_group_name  = local.s3_backup_cw_log_group_name
            log_stream_name = local.s3_backup_cw_log_stream_name
          }
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }
    }
  }

  dynamic "redshift_configuration" {
    for_each = local.destination == "redshift" ? [1] : []
    content {
      role_arn           = local.firehose_role_arn
      cluster_jdbcurl    = "jdbc:redshift://${var.redshift_cluster_endpoint}/${var.redshift_database_name}"
      username           = var.redshift_username
      password           = var.redshift_password
      data_table_name    = var.redshift_table_name
      copy_options       = var.redshift_copy_options
      data_table_columns = var.redshift_data_table_columns
      s3_backup_mode     = local.s3_backup
      retry_duration     = var.redshift_retry_duration

      s3_configuration {
        role_arn            = !local.use_backup_vars_in_s3_configuration ? local.firehose_role_arn : local.s3_backup_role_arn
        bucket_arn          = !local.use_backup_vars_in_s3_configuration ? var.s3_bucket_arn : var.s3_backup_bucket_arn
        buffering_size      = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_size : var.s3_backup_buffering_size
        buffering_interval  = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_interval : var.s3_backup_buffering_interval
        compression_format  = !local.use_backup_vars_in_s3_configuration ? var.s3_compression_format : var.s3_backup_compression
        prefix              = !local.use_backup_vars_in_s3_configuration ? var.s3_prefix : var.s3_backup_prefix
        error_output_prefix = !local.use_backup_vars_in_s3_configuration ? var.s3_error_output_prefix : var.s3_backup_error_output_prefix
        kms_key_arn         = (!local.use_backup_vars_in_s3_configuration && var.enable_s3_encryption ? var.s3_kms_key_arn : (local.use_backup_vars_in_s3_configuration && var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null))

      }

      dynamic "s3_backup_configuration" {
        for_each = var.enable_s3_backup ? [1] : []
        content {
          bucket_arn          = var.s3_backup_bucket_arn
          role_arn            = local.s3_backup_role_arn
          prefix              = var.s3_backup_prefix
          buffering_size      = var.s3_backup_buffering_size
          buffering_interval  = var.s3_backup_buffering_interval
          compression_format  = var.s3_backup_compression
          error_output_prefix = var.s3_backup_error_output_prefix
          kms_key_arn         = var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null
          cloudwatch_logging_options {
            enabled         = var.s3_backup_enable_log
            log_group_name  = local.s3_backup_cw_log_group_name
            log_stream_name = local.s3_backup_cw_log_stream_name
          }
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "secrets_manager_configuration" {
        for_each = var.enable_secrets_manager ? [1] : []
        content {
          enabled    = var.enable_secrets_manager
          secret_arn = var.secret_arn
          role_arn   = local.firehose_role_arn
        }
      }

    }
  }

  dynamic "splunk_configuration" {
    for_each = local.destination == "splunk" ? [1] : []
    content {
      hec_endpoint               = var.waf.splunk_hec_endpoint
      hec_token                  = var.waf.splunk_hec_token
      hec_acknowledgment_timeout = var.splunk_hec_acknowledgment_timeout
      hec_endpoint_type          = var.splunk_hec_endpoint_type
      retry_duration             = var.splunk_retry_duration
      s3_backup_mode             = local.s3_backup_mode

      s3_configuration {
        role_arn            = !local.use_backup_vars_in_s3_configuration ? local.firehose_role_arn : local.s3_backup_role_arn
        bucket_arn          = !local.use_backup_vars_in_s3_configuration ? var.s3_bucket_arn : var.s3_backup_bucket_arn
        buffering_size      = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_size : var.s3_backup_buffering_size
        buffering_interval  = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_interval : var.s3_backup_buffering_interval
        compression_format  = !local.use_backup_vars_in_s3_configuration ? var.s3_compression_format : var.s3_backup_compression
        prefix              = !local.use_backup_vars_in_s3_configuration ? var.s3_prefix : var.s3_backup_prefix
        error_output_prefix = !local.use_backup_vars_in_s3_configuration ? var.s3_error_output_prefix : var.s3_backup_error_output_prefix
        kms_key_arn         = (!local.use_backup_vars_in_s3_configuration && var.enable_s3_encryption ? var.s3_kms_key_arn : (local.use_backup_vars_in_s3_configuration && var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null))
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }

      dynamic "secrets_manager_configuration" {
        for_each = var.enable_secrets_manager ? [1] : []
        content {
          enabled    = var.enable_secrets_manager
          secret_arn = var.secret_arn
          role_arn   = local.firehose_role_arn
        }
      }
    }
  }

  dynamic "http_endpoint_configuration" {
    for_each = local.destination == "http_endpoint" ? [1] : []
    content {
      url                = local.http_endpoint_url[var.destination]
      name               = local.http_endpoint_name[var.destination]
      access_key         = var.destination != "sumologic" ? var.http_endpoint_access_key : null
      buffering_size     = var.buffering_size
      buffering_interval = var.buffering_interval
      role_arn           = local.firehose_role_arn
      s3_backup_mode     = local.s3_backup_mode
      retry_duration     = var.http_endpoint_retry_duration

      s3_configuration {
        role_arn            = !local.use_backup_vars_in_s3_configuration ? local.firehose_role_arn : local.s3_backup_role_arn
        bucket_arn          = !local.use_backup_vars_in_s3_configuration ? var.s3_bucket_arn : var.s3_backup_bucket_arn
        buffering_size      = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_size : var.s3_backup_buffering_size
        buffering_interval  = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_interval : var.s3_backup_buffering_interval
        compression_format  = !local.use_backup_vars_in_s3_configuration ? var.s3_compression_format : var.s3_backup_compression
        prefix              = !local.use_backup_vars_in_s3_configuration ? var.s3_prefix : var.s3_backup_prefix
        error_output_prefix = !local.use_backup_vars_in_s3_configuration ? var.s3_error_output_prefix : var.s3_backup_error_output_prefix
        kms_key_arn         = (!local.use_backup_vars_in_s3_configuration && var.enable_s3_encryption ? var.s3_kms_key_arn : (local.use_backup_vars_in_s3_configuration && var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null))
      }

      dynamic "request_configuration" {
        for_each = var.http_endpoint_enable_request_configuration ? [1] : []
        content {
          content_encoding = var.http_endpoint_request_configuration_content_encoding

          dynamic "common_attributes" {
            for_each = concat(var.http_endpoint_request_configuration_common_attributes, try(local.http_endpoint_destinations_parameters[var.destination], []))
            content {
              name  = common_attributes.value.name
              value = common_attributes.value.value
            }
          }

        }
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }

      dynamic "secrets_manager_configuration" {
        for_each = var.enable_secrets_manager ? [1] : []
        content {
          enabled    = var.enable_secrets_manager
          secret_arn = var.secret_arn
          role_arn   = local.firehose_role_arn
        }
      }
    }
  }

  dynamic "elasticsearch_configuration" {
    for_each = local.destination == "elasticsearch" ? [1] : []
    content {
      domain_arn            = var.elasticsearch_domain_arn
      role_arn              = local.firehose_role_arn
      index_name            = var.elasticsearch_index_name
      index_rotation_period = var.elasticsearch_index_rotation_period
      retry_duration        = var.elasticsearch_retry_duration
      type_name             = var.elasticsearch_type_name
      buffering_interval    = var.buffering_interval
      buffering_size        = var.buffering_size
      s3_backup_mode        = local.s3_backup_mode

      s3_configuration {
        role_arn            = !local.use_backup_vars_in_s3_configuration ? local.firehose_role_arn : local.s3_backup_role_arn
        bucket_arn          = !local.use_backup_vars_in_s3_configuration ? var.s3_bucket_arn : var.s3_backup_bucket_arn
        buffering_size      = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_size : var.s3_backup_buffering_size
        buffering_interval  = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_interval : var.s3_backup_buffering_interval
        compression_format  = !local.use_backup_vars_in_s3_configuration ? var.s3_compression_format : var.s3_backup_compression
        prefix              = !local.use_backup_vars_in_s3_configuration ? var.s3_prefix : var.s3_backup_prefix
        error_output_prefix = !local.use_backup_vars_in_s3_configuration ? var.s3_error_output_prefix : var.s3_backup_error_output_prefix
        kms_key_arn         = (!local.use_backup_vars_in_s3_configuration && var.enable_s3_encryption ? var.s3_kms_key_arn : (local.use_backup_vars_in_s3_configuration && var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null))
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }

      dynamic "vpc_config" {
        for_each = var.enable_vpc ? [1] : []
        content {
          role_arn           = local.vpc_role_arn
          subnet_ids         = var.vpc_subnet_ids
          security_group_ids = local.search_destination_vpc_sgs
        }
      }

    }
  }

  dynamic "opensearch_configuration" {
    for_each = local.destination == "opensearch" ? [1] : []
    content {
      domain_arn            = var.opensearch_domain_arn
      role_arn              = local.firehose_role_arn
      index_name            = var.opensearch_index_name
      index_rotation_period = var.opensearch_index_rotation_period
      retry_duration        = var.opensearch_retry_duration
      type_name             = var.opensearch_type_name
      buffering_interval    = var.buffering_interval
      buffering_size        = var.buffering_size
      s3_backup_mode        = local.s3_backup_mode

      s3_configuration {
        role_arn            = !local.use_backup_vars_in_s3_configuration ? local.firehose_role_arn : local.s3_backup_role_arn
        bucket_arn          = !local.use_backup_vars_in_s3_configuration ? var.s3_bucket_arn : var.s3_backup_bucket_arn
        buffering_size      = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_size : var.s3_backup_buffering_size
        buffering_interval  = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_interval : var.s3_backup_buffering_interval
        compression_format  = !local.use_backup_vars_in_s3_configuration ? var.s3_compression_format : var.s3_backup_compression
        prefix              = !local.use_backup_vars_in_s3_configuration ? var.s3_prefix : var.s3_backup_prefix
        error_output_prefix = !local.use_backup_vars_in_s3_configuration ? var.s3_error_output_prefix : var.s3_backup_error_output_prefix
        kms_key_arn         = (!local.use_backup_vars_in_s3_configuration && var.enable_s3_encryption ? var.s3_kms_key_arn : (local.use_backup_vars_in_s3_configuration && var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null))
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }

      dynamic "vpc_config" {
        for_each = var.enable_vpc ? [1] : []
        content {
          role_arn           = local.vpc_role_arn
          subnet_ids         = var.vpc_subnet_ids
          security_group_ids = local.search_destination_vpc_sgs
        }
      }

      document_id_options {
        default_document_id_format = var.opensearch_document_id_options
      }

    }
  }

  dynamic "opensearchserverless_configuration" {
    for_each = local.destination == "opensearchserverless" ? [1] : []
    content {

      collection_endpoint = var.opensearchserverless_collection_endpoint
      index_name          = var.opensearch_index_name
      buffering_interval  = var.buffering_interval
      buffering_size      = var.buffering_size
      retry_duration      = var.opensearch_retry_duration
      role_arn            = local.firehose_role_arn
      s3_backup_mode      = local.s3_backup_mode

      s3_configuration {
        role_arn            = !local.use_backup_vars_in_s3_configuration ? local.firehose_role_arn : local.s3_backup_role_arn
        bucket_arn          = !local.use_backup_vars_in_s3_configuration ? var.s3_bucket_arn : var.s3_backup_bucket_arn
        buffering_size      = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_size : var.s3_backup_buffering_size
        buffering_interval  = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_interval : var.s3_backup_buffering_interval
        compression_format  = !local.use_backup_vars_in_s3_configuration ? var.s3_compression_format : var.s3_backup_compression
        prefix              = !local.use_backup_vars_in_s3_configuration ? var.s3_prefix : var.s3_backup_prefix
        error_output_prefix = !local.use_backup_vars_in_s3_configuration ? var.s3_error_output_prefix : var.s3_backup_error_output_prefix
        kms_key_arn         = (!local.use_backup_vars_in_s3_configuration && var.enable_s3_encryption ? var.s3_kms_key_arn : (local.use_backup_vars_in_s3_configuration && var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null))
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }

      dynamic "vpc_config" {
        for_each = var.enable_vpc ? [1] : []
        content {
          role_arn           = local.vpc_role_arn
          subnet_ids         = var.vpc_subnet_ids
          security_group_ids = local.search_destination_vpc_sgs
        }
      }

    }
  }

  dynamic "snowflake_configuration" {
    for_each = local.destination == "snowflake" ? [1] : []
    content {
      account_url          = "https://${var.snowflake_account_identifier}.snowflakecomputing.com"
      database             = var.snowflake_database
      private_key          = var.snowflake_private_key
      key_passphrase       = var.snowflake_key_passphrase
      role_arn             = local.firehose_role_arn
      schema               = var.snowflake_schema
      table                = var.snowflake_table
      user                 = var.snowflake_user
      data_loading_option  = var.snowflake_data_loading_option
      metadata_column_name = var.snowflake_metadata_column_name
      content_column_name  = var.snowflake_content_column_name
      s3_backup_mode       = local.s3_backup_mode
      retry_duration       = var.snowflake_retry_duration

      snowflake_role_configuration {
        enabled        = var.snowflake_role_configuration_enabled
        snowflake_role = var.snowflake_role_configuration_role
      }

      s3_configuration {
        role_arn            = !local.use_backup_vars_in_s3_configuration ? local.firehose_role_arn : local.s3_backup_role_arn
        bucket_arn          = !local.use_backup_vars_in_s3_configuration ? var.s3_bucket_arn : var.s3_backup_bucket_arn
        buffering_size      = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_size : var.s3_backup_buffering_size
        buffering_interval  = !local.use_backup_vars_in_s3_configuration ? var.s3_configuration_buffering_interval : var.s3_backup_buffering_interval
        compression_format  = !local.use_backup_vars_in_s3_configuration ? var.s3_compression_format : var.s3_backup_compression
        prefix              = !local.use_backup_vars_in_s3_configuration ? var.s3_prefix : var.s3_backup_prefix
        error_output_prefix = !local.use_backup_vars_in_s3_configuration ? var.s3_error_output_prefix : var.s3_backup_error_output_prefix
        kms_key_arn         = (!local.use_backup_vars_in_s3_configuration && var.enable_s3_encryption ? var.s3_kms_key_arn : (local.use_backup_vars_in_s3_configuration && var.s3_backup_enable_encryption ? var.s3_backup_kms_key_arn : null))
      }

      dynamic "snowflake_vpc_configuration" {
        for_each = var.snowflake_private_link_vpce_id != null ? [1] : []
        content {
          private_link_vpce_id = var.snowflake_private_link_vpce_id
        }
      }

      dynamic "cloudwatch_logging_options" {
        for_each = var.enable_destination_log ? [1] : []
        content {
          enabled         = var.enable_destination_log
          log_group_name  = local.destination_cw_log_group_name
          log_stream_name = local.destination_cw_log_stream_name
        }
      }

      dynamic "processing_configuration" {
        for_each = local.enable_processing ? [1] : []
        content {
          enabled = local.enable_processing
          dynamic "processors" {
            for_each = local.processors
            content {
              type = processors.value["type"]
              dynamic "parameters" {
                for_each = processors.value["parameters"]
                content {
                  parameter_name  = parameters.value["name"]
                  parameter_value = parameters.value["value"]
                }
              }
            }
          }
        }
      }

      dynamic "secrets_manager_configuration" {
        for_each = var.enable_secrets_manager ? [1] : []
        content {
          enabled    = var.enable_secrets_manager
          secret_arn = var.secret_arn
          role_arn   = local.firehose_role_arn
        }
      }
    }
  }

  tags = var.tags

}

##################
# Cloudwatch
##################
resource "aws_cloudwatch_log_group" "log" {
  count             = local.create_destination_logs || local.create_backup_logs ? 1 : 0
  name              = local.cw_log_group_name
  retention_in_days = var.cw_log_retention_in_days
  tags              = merge(var.tags, var.cw_tags)
}

resource "aws_cloudwatch_log_stream" "backup" {
  count          = local.create_backup_logs ? 1 : 0
  name           = local.cw_log_backup_stream_name
  log_group_name = aws_cloudwatch_log_group.log[0].name
}

resource "aws_cloudwatch_log_stream" "destination" {
  count          = local.create_destination_logs ? 1 : 0
  name           = local.destination_cw_log_stream_name
  log_group_name = aws_cloudwatch_log_group.log[0].name
}

##################
# Security Group
##################
resource "aws_security_group" "firehose" {
  count       = local.search_destination_vpc_create_firehose_sg ? 1 : 0
  name        = "${var.general.key_name}-sg"
  description = !var.vpc_security_group_same_as_destination ? "Security group to kinesis firehose" : "Security Group to kinesis firehose and destination"
  vpc_id      = var.enable_vpc ? data.aws_subnet.subnet[0].vpc_id : var.vpc_security_group_destination_vpc_id

  dynamic "ingress" {
    for_each = var.vpc_security_group_same_as_destination ? [1] : []
    content {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      self        = true
      description = "Allow Inbound HTTPS Traffic"
    }
  }

  tags = merge(var.tags, var.vpc_security_group_tags)
}

resource "aws_security_group_rule" "firehose_egress_rule" {
  for_each                 = local.search_destination_vpc_create_firehose_sg && !var.vpc_security_group_same_as_destination ? (local.vpc_create_destination_group ? { for key, value in [aws_security_group.destination[0].id] : key => value } : { for key, value in var.vpc_security_group_destination_ids : key => value }) : {}
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.firehose[0].id
  source_security_group_id = each.value
  description              = "Allow Outbound HTTPS Traffic for destination"
}

resource "aws_security_group" "destination" {
  count       = local.vpc_create_destination_group ? 1 : 0
  name        = "${var.general.key_name}-destination-sg"
  description = "Allow Inbound traffic from kinesis firehose stream"
  vpc_id      = local.is_search_destination && var.enable_vpc ? data.aws_subnet.subnet[0].vpc_id : var.vpc_security_group_destination_vpc_id

  dynamic "ingress" {
    for_each = local.is_search_destination ? [1] : []
    content {
      from_port       = 443
      to_port         = 443
      protocol        = "tcp"
      security_groups = local.search_destination_vpc_sgs
      description     = "Allow inbound traffic from Kinesis Firehose"
    }
  }

  dynamic "ingress" {
    for_each = !local.is_search_destination ? [1] : []
    content {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = local.firehose_cidr_blocks[local.destination][data.aws_region.current.name]
      description = "Allow inbound traffic from Kinesis Firehose"
    }
  }

  tags = merge(var.tags, var.vpc_security_group_tags)
}

resource "aws_security_group_rule" "firehose" {
  for_each                 = local.search_destination_vpc_configure_existing_firehose_sg ? (var.vpc_security_group_same_as_destination ? toset(var.vpc_security_group_firehose_ids) : toset(flatten([for security_group in var.vpc_security_group_firehose_ids : [for destination_sg in local.search_destination_vpc_destination_sgs : "${security_group}_${destination_sg}"]]))) : toset([])
  type                     = var.vpc_security_group_same_as_destination ? "ingress" : "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = var.vpc_security_group_same_as_destination ? each.value : split("_", each.value)[0]
  source_security_group_id = !var.vpc_security_group_same_as_destination ? split("_", each.value)[1] : null
  self                     = var.vpc_security_group_same_as_destination ? true : false
  description              = var.vpc_security_group_same_as_destination ? "Allow Inbound HTTPS Traffic" : "Allow Outbound HTTPS Traffic"
}

resource "aws_security_group_rule" "destination" {
  for_each                 = local.vpc_configure_destination_group ? (local.is_search_destination ? flatten([for security_group in var.vpc_security_group_destination_ids : [for destination_sg in local.search_destination_vpc_firehose_sgs : "${security_group}_${destination_sg}"]]) : { for key, value in var.vpc_security_group_destination_ids : key => value }) : {}
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  cidr_blocks              = !local.is_search_destination ? local.firehose_cidr_blocks[local.destination][data.aws_region.current.name] : null
  security_group_id        = local.is_search_destination ? split("_", each.value)[0] : each.value
  source_security_group_id = local.is_search_destination ? split("_", each.value)[1] : null
  description              = "Allow Inbound HTTPS Traffic from Firehose"
}
