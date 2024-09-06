variable "waf" {}

variable "create" {
  description = "Controls if kinesis firehose should be created (it affects almost all resources)"
  type        = bool
  default     = true
}

variable "input_source" {
  description = "This is the kinesis firehose source"
  type        = string
  default     = "direct-put"
  validation {
    error_message = "Please use a valid source!"
    condition     = contains(["direct-put", "kinesis", "waf", "msk"], var.input_source)
  }
}

variable "destination" {
  description = "This is the destination to where the data is delivered"
  type        = string
  validation {
    error_message = "Please use a valid destination!"
    condition     = contains(["s3", "extended_s3", "redshift", "opensearch", "opensearchserverless", "elasticsearch", "splunk", "http_endpoint", "datadog", "coralogix", "newrelic", "dynatrace", "honeycomb", "logicmonitor", "mongodb", "sumologic", "snowflake"], var.destination)
  }
}

variable "create_role" {
  description = "Controls whether IAM role for Kinesis Firehose Stream should be created"
  type        = bool
  default     = true
}

variable "tags" {
  description = "A map of tags to assign to resources."
  type        = map(string)
  default     = {}
}
######
# All Destinations
######
variable "buffering_size" {
  description = "Buffer incoming data to the specified size, in MBs, before delivering it to the destination."
  type        = number
  default     = 5
  validation {
    error_message = "Valid values: minimum: 1 MiB, maximum: 128 MiB."
    condition     = var.buffering_size >= 1 && var.buffering_size <= 128
  }
}

variable "buffering_interval" {
  description = "Buffer incoming data for the specified period of time, in seconds, before delivering it to the destination"
  type        = number
  default     = 60
  validation {
    error_message = "Valid Values: Minimum: 0 seconds, maximum: 900 seconds."
    condition     = var.buffering_interval >= 0 && var.buffering_interval <= 900
  }
}

variable "enable_lambda_transform" {
  description = "Set it to true to enable data transformation with lambda"
  type        = bool
  default     = false
}

variable "transform_lambda_arn" {
  description = "Lambda ARN to Transform source records"
  type        = string
  default     = null
}

variable "transform_lambda_role_arn" {
  description = "The ARN of the role to execute the transform lambda. If null use the Firehose Stream role"
  type        = string
  default     = null
}

variable "transform_lambda_buffer_size" {
  description = "The AWS Lambda function has a 6 MB invocation payload quota. Your data can expand in size after it's processed by the AWS Lambda function. A smaller buffer size allows for more room should the data expand after processing."
  type        = number
  default     = null
  validation {
    error_message = "Valid Values: minimum: 1 MB, maximum: 3 MB."
    condition     = var.transform_lambda_buffer_size == null || (coalesce(var.transform_lambda_buffer_size, 1) >= 1 && coalesce(var.transform_lambda_buffer_size, 1) <= 3)
  }
}

variable "transform_lambda_buffer_interval" {
  description = "The period of time during which Kinesis Data Firehose buffers incoming data before invoking the AWS Lambda function. The AWS Lambda function is invoked once the value of the buffer size or the buffer interval is reached."
  type        = number
  default     = null
  validation {
    error_message = "Valid Values: minimum: 60 seconds, maximum: 900 seconds."
    condition     = var.transform_lambda_buffer_interval == null || (coalesce(var.transform_lambda_buffer_interval, 60) >= 60 && coalesce(var.transform_lambda_buffer_interval, 60) <= 900)
  }
}

variable "transform_lambda_number_retries" {
  description = "Number of retries for AWS Transformation lambda"
  type        = number
  default     = null
  validation {
    error_message = "Number of retries for lambda must be between 0 and 300."
    condition     = var.transform_lambda_number_retries == null || (coalesce(var.transform_lambda_number_retries, 3) >= 0 && coalesce(var.transform_lambda_number_retries, 3) <= 300)
  }
}

variable "s3_configuration_buffering_size" {
  description = "Buffer incoming data to the specified size, in MBs, before delivering it to the destination. The default value is 5. We recommend setting SizeInMBs to a value greater than the amount of data you typically ingest into the delivery stream in 10 seconds. For example, if you typically ingest data at 1 MB/sec set SizeInMBs to be 10 MB or higher."
  type        = number
  default     = 5
  validation {
    error_message = "Valid values: minimum: 1 MiB, maximum: 128 MiB."
    condition     = var.s3_configuration_buffering_size >= 1 && var.s3_configuration_buffering_size <= 128
  }
}

variable "s3_configuration_buffering_interval" {
  description = "Buffer incoming data for the specified period of time, in seconds, before delivering it to the destination."
  type        = number
  default     = 300
  validation {
    error_message = "Valid Values: Minimum: 60 seconds, maximum: 900 seconds."
    condition     = var.s3_configuration_buffering_interval >= 60 && var.s3_configuration_buffering_interval <= 900
  }
}

variable "enable_s3_backup" {
  description = "The Amazon S3 backup mode"
  type        = bool
  default     = false
}

variable "s3_backup_bucket_arn" {
  description = "The ARN of the S3 backup bucket"
  type        = string
  default     = null
}

variable "s3_backup_prefix" {
  description = "The YYYY/MM/DD/HH time format prefix is automatically used for delivered S3 files. You can specify an extra prefix to be added in front of the time format prefix. Note that if the prefix ends with a slash, it appears as a folder in the S3 bucket"
  type        = string
  default     = "backup/"
}

variable "s3_backup_buffering_size" {
  description = "Buffer incoming data to the specified size, in MBs, before delivering it to the destination."
  type        = number
  default     = 100
  validation {
    error_message = "Valid values: minimum: 1 MiB, maximum: 128 MiB."
    condition     = var.s3_backup_buffering_size >= 1 && var.s3_backup_buffering_size <= 128
  }
}

variable "s3_backup_buffering_interval" {
  description = "Buffer incoming data for the specified period of time, in seconds, before delivering it to the destination."
  type        = number
  default     = 100
  validation {
    error_message = "Valid Values: Minimum: 60 seconds, maximum: 900 seconds."
    condition     = var.s3_backup_buffering_interval >= 60 && var.s3_backup_buffering_interval <= 900
  }
}

variable "s3_backup_compression" {
  description = "The compression format"
  type        = string
  default     = "GZIP"
  validation {
    error_message = "Valid values are UNCOMPRESSED, GZIP, ZIP, Snappy and HADOOP_SNAPPY."
    condition     = contains(["UNCOMPRESSED", "GZIP", "ZIP", "Snappy", "HADOOP_SNAPPY"], var.s3_backup_compression)
  }
}

variable "s3_backup_error_output_prefix" {
  description = "Prefix added to failed records before writing them to S3"
  type        = string
  default     = null
}

variable "s3_backup_enable_encryption" {
  description = "Indicates if want enable KMS Encryption in S3 Backup Bucket."
  type        = bool
  default     = true
}

variable "s3_backup_kms_key_arn" {
  description = "Specifies the KMS key ARN the stream will use to encrypt data. If not set, no encryption will be used."
  type        = string
  default     = null
}

variable "s3_backup_use_existing_role" {
  description = "Indicates if want use the kinesis firehose role to s3 backup bucket access."
  type        = bool
  default     = true
}

variable "s3_backup_role_arn" {
  description = "The role that Kinesis Data Firehose can use to access S3 Backup."
  type        = string
  default     = null
}

variable "s3_backup_enable_log" {
  description = "Enables or disables the logging"
  type        = bool
  default     = true
}

variable "s3_backup_create_cw_log_group" {
  description = "Enables or disables the cloudwatch log group creation"
  type        = bool
  default     = true
}

variable "s3_backup_log_group_name" {
  description = "he CloudWatch group name for logging"
  type        = string
  default     = null
}

variable "s3_backup_log_stream_name" {
  description = "The CloudWatch log stream name for logging"
  type        = string
  default     = null
}

variable "s3_backup_mode" {
  description = "Defines how documents should be delivered to Amazon S3. Used to elasticsearch, opensearch, splunk, http configurations. For S3 and Redshift use enable_s3_backup"
  type        = string
  default     = "All"
  validation {
    error_message = "Valid values are FailedOnly and All."
    condition     = contains(["FailedOnly", "All"], var.s3_backup_mode)
  }
}

variable "enable_destination_log" {
  description = "The CloudWatch Logging Options for the delivery stream"
  type        = bool
  default     = true
}

variable "create_destination_cw_log_group" {
  description = "Enables or disables the cloudwatch log group creation to destination"
  type        = bool
  default     = true
}

variable "destination_log_group_name" {
  description = "The CloudWatch group name for destination logs"
  type        = string
  default     = null
}

variable "destination_log_stream_name" {
  description = "The CloudWatch log stream name for destination logs"
  type        = string
  default     = null
}

variable "cw_log_retention_in_days" {
  description = "Specifies the number of days you want to retain log events in the specified log group. Possible values are: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, and 3653."
  type        = number
  default     = null
}

variable "cw_tags" {
  description = "A map of tags to assign to the resource."
  type        = map(string)
  default     = {}
}

variable "s3_bucket_arn" {
  description = "The ARN of the S3 destination bucket"
  type        = string
  default     = null
}

variable "s3_prefix" {
  description = "The YYYY/MM/DD/HH time format prefix is automatically used for delivered S3 files. You can specify an extra prefix to be added in front of the time format prefix. Note that if the prefix ends with a slash, it appears as a folder in the S3 bucket"
  type        = string
  default     = null
}

variable "s3_error_output_prefix" {
  description = "Prefix added to failed records before writing them to S3. This prefix appears immediately following the bucket name."
  type        = string
  default     = null
}

variable "enable_s3_encryption" {
  description = "Indicates if want use encryption in S3 bucket."
  type        = bool
  default     = true
}

variable "s3_kms_key_arn" {
  description = "Specifies the KMS key ARN the stream will use to encrypt data. If not set, no encryption will be used"
  type        = string
  default     = null
}

variable "s3_compression_format" {
  description = "The compression format"
  type        = string
  default     = "UNCOMPRESSED"
  validation {
    error_message = "Valid values are UNCOMPRESSED, GZIP, ZIP, Snappy and HADOOP_SNAPPY."
    condition     = contains(["UNCOMPRESSED", "GZIP", "ZIP", "Snappy", "HADOOP_SNAPPY"], var.s3_compression_format)
  }
}

variable "s3_own_bucket" {
  description = "Indicates if you own the bucket. If not, will be configure permissions to grants the bucket owner full access to the objects delivered by Kinesis Data Firehose"
  type        = bool
  default     = true
}

variable "s3_cross_account" {
  description = "Indicates if S3 bucket destination is in a different account"
  type        = bool
  default     = false
}

variable "destination_cross_account" {
  description = "Indicates if destination is in a different account. Only supported to Elasticsearch and OpenSearch"
  type        = bool
  default     = false
}

variable "enable_sse" {
  description = "Whether to enable encryption at rest. Only makes sense when source is Direct Put"
  type        = bool
  default     = false
}

variable "sse_kms_key_type" {
  description = "Type of encryption key."
  type        = string
  default     = "AWS_OWNED_CMK"
  validation {
    error_message = "Valid values are AWS_OWNED_CMK and CUSTOMER_MANAGED_CMK."
    condition     = contains(["AWS_OWNED_CMK", "CUSTOMER_MANAGED_CMK"], var.sse_kms_key_type)
  }
}

variable "sse_kms_key_arn" {
  description = "Amazon Resource Name (ARN) of the encryption key"
  type        = string
  default     = null
}

######
# Source Common Variables
######
variable "source_role_arn" {
  description = "The ARN of the role that provides access to the source. Only Supported on Kinesis and MSK Sources"
  type        = string
  default     = null
}

variable "source_use_existing_role" {
  description = "Indicates if want use the kinesis firehose role for sources access. Only Supported on Kinesis and MSK Sources"
  type        = bool
  default     = true
}

######
# Kinesis Source
######
variable "kinesis_source_stream_arn" {
  description = "The kinesis stream used as the source of the firehose delivery stream"
  type        = string
  default     = null
}

variable "kinesis_source_role_arn" { # TODO: Deprecated. Remove Next Major Version
  description = "DEPRECATED!! Use variable instead source_role_arn! The ARN of the role that provides access to the source Kinesis stream"
  type        = string
  default     = null
}

variable "kinesis_source_use_existing_role" { # TODO: Deprecated. Remove Next Major Version
  description = "DEPRECATED!! Use variable source_use_existing_role instead! Indicates if want use the kinesis firehose role to kinesis data stream access."
  type        = bool
  default     = true
}

variable "kinesis_source_is_encrypted" {
  description = "Indicates if Kinesis data stream source is encrypted"
  type        = bool
  default     = false
}

variable "kinesis_source_kms_arn" {
  description = "Kinesis Source KMS Key to add Firehose role to decrypt the records."
  type        = string
  default     = null
}

######
# MSK Source
######
variable "msk_source_cluster_arn" {
  description = "The ARN of the Amazon MSK cluster."
  type        = string
  default     = null
}

variable "msk_source_topic_name" {
  description = "The topic name within the Amazon MSK cluster."
  type        = string
  default     = null
}

variable "msk_source_connectivity_type" {
  description = "The type of connectivity used to access the Amazon MSK cluster. Valid values: PUBLIC, PRIVATE."
  type        = string
  default     = "PUBLIC"
  validation {
    error_message = "Valid values are PUBLIC and PRIVATE."
    condition     = contains(["PUBLIC", "PRIVATE"], var.msk_source_connectivity_type)
  }
}
######
# S3 Destination Configurations
######
variable "enable_cloudwatch_logs_decompression" {
  description = "Enables or disables Cloudwatch Logs decompression"
  type        = bool
  default     = false
}

variable "enable_cloudwatch_logs_data_message_extraction" {
  description = "Cloudwatch Logs data message extraction"
  type        = bool
  default     = false
}

variable "enable_dynamic_partitioning" {
  description = "Enables or disables dynamic partitioning"
  type        = bool
  default     = false
}

variable "dynamic_partitioning_retry_duration" {
  description = "Total amount of seconds Firehose spends on retries"
  type        = number
  default     = 300
  validation {
    error_message = "Valid values between 0 and 7200."
    condition     = var.dynamic_partitioning_retry_duration >= 0 && var.dynamic_partitioning_retry_duration <= 7200
  }
}

variable "dynamic_partition_append_delimiter_to_record" { # TODO Variable Deprecated. Remove on Next Major Version
  description = "DEPRECATED!! Use var append_delimiter_to_record instead!! Use To configure your delivery stream to add a new line delimiter between records in objects that are delivered to Amazon S3."
  type        = bool
  default     = false
}

variable "dynamic_partition_metadata_extractor_query" {
  description = "Dynamic Partition JQ query."
  type        = string
  default     = null
}

variable "dynamic_partition_enable_record_deaggregation" {
  description = "Data deaggregation is the process of parsing through the records in a delivery stream and separating the records based either on valid JSON or on the specified delimiter"
  type        = bool
  default     = false
}

variable "dynamic_partition_record_deaggregation_type" {
  description = "Data deaggregation is the process of parsing through the records in a delivery stream and separating the records based either on valid JSON or on the specified delimiter"
  type        = string
  default     = "JSON"
  validation {
    error_message = "Valid values are JSON and DELIMITED."
    condition     = contains(["JSON", "DELIMITED"], var.dynamic_partition_record_deaggregation_type)
  }
}

variable "dynamic_partition_record_deaggregation_delimiter" {
  description = "Specifies the delimiter to be used for parsing through the records in the delivery stream and deaggregating them"
  type        = string
  default     = null
}

variable "enable_data_format_conversion" {
  description = "Set it to true if you want to disable format conversion."
  type        = bool
  default     = false
}

variable "data_format_conversion_glue_database" {
  description = "Name of the AWS Glue database that contains the schema for the output data."
  type        = string
  default     = null
}

variable "data_format_conversion_glue_use_existing_role" {
  description = "Indicates if want use the kinesis firehose role to glue access."
  type        = bool
  default     = true
}

variable "data_format_conversion_glue_role_arn" {
  description = "The role that Kinesis Data Firehose can use to access AWS Glue. This role must be in the same account you use for Kinesis Data Firehose. Cross-account roles aren't allowed."
  type        = string
  default     = null
}

variable "data_format_conversion_glue_table_name" {
  description = "Specifies the AWS Glue table that contains the column information that constitutes your data schema"
  type        = string
  default     = null
}

variable "data_format_conversion_glue_catalog_id" {
  description = "The ID of the AWS Glue Data Catalog. If you don't supply this, the AWS account ID is used by default."
  type        = string
  default     = null
}

variable "data_format_conversion_glue_region" {
  description = "If you don't specify an AWS Region, the default is the current region."
  type        = string
  default     = null
}

variable "data_format_conversion_glue_version_id" {
  description = "Specifies the table version for the output data schema."
  type        = string
  default     = "LATEST"
}

variable "data_format_conversion_input_format" {
  description = "Specifies which deserializer to use. You can choose either the Apache Hive JSON SerDe or the OpenX JSON SerDe"
  type        = string
  default     = "OpenX"
  validation {
    error_message = "Valid values are HIVE and OPENX."
    condition     = contains(["HIVE", "OpenX"], var.data_format_conversion_input_format)
  }
}

variable "data_format_conversion_openx_case_insensitive" {
  description = "When set to true, Kinesis Data Firehose converts JSON keys to lowercase before deserializing them."
  type        = bool
  default     = true
}

variable "data_format_conversion_openx_convert_dots_to_underscores" {
  description = "Specifies that the names of the keys include dots and that you want Kinesis Data Firehose to replace them with underscores. This is useful because Apache Hive does not allow dots in column names."
  type        = bool
  default     = false
}

variable "data_format_conversion_openx_column_to_json_key_mappings" {
  description = "A map of column names to JSON keys that aren't identical to the column names. This is useful when the JSON contains keys that are Hive keywords."
  type        = map(string)
  default     = null
}

variable "data_format_conversion_hive_timestamps" {
  description = "A list of how you want Kinesis Data Firehose to parse the date and time stamps that may be present in your input data JSON. To specify these format strings, follow the pattern syntax of JodaTime's DateTimeFormat format strings."
  type        = list(string)
  default     = []
}

variable "data_format_conversion_output_format" {
  description = "Specifies which serializer to use. You can choose either the ORC SerDe or the Parquet SerDe"
  type        = string
  default     = "PARQUET"
  validation {
    error_message = "Valid values are ORC and PARQUET."
    condition     = contains(["ORC", "PARQUET"], var.data_format_conversion_output_format)
  }
}

variable "data_format_conversion_block_size" {
  description = "The Hadoop Distributed File System (HDFS) block size. This is useful if you intend to copy the data from Amazon S3 to HDFS before querying. The Value is in Bytes."
  type        = number
  default     = 268435456
  validation {
    error_message = "Minimum Value is 64 MiB."
    condition     = var.data_format_conversion_block_size >= 67108864
  }
}

variable "data_format_conversion_parquet_compression" {
  description = "The compression code to use over data blocks."
  type        = string
  default     = "SNAPPY"
  validation {
    error_message = "Valid values are UNCOMPRESSED, SNAPPY and GZIP."
    condition     = contains(["UNCOMPRESSED", "SNAPPY", "GZIP"], var.data_format_conversion_parquet_compression)
  }
}

variable "data_format_conversion_parquet_dict_compression" {
  description = "Indicates whether to enable dictionary compression."
  type        = bool
  default     = false
}

variable "data_format_conversion_parquet_max_padding" {
  description = "The maximum amount of padding to apply. This is useful if you intend to copy the data from Amazon S3 to HDFS before querying. The value is in bytes"
  type        = number
  default     = 0
}

variable "data_format_conversion_parquet_page_size" {
  description = "Column chunks are divided into pages. A page is conceptually an indivisible unit (in terms of compression and encoding). The value is in bytes"
  type        = number
  default     = 1048576
  validation {
    error_message = "Minimum Value is 64 KiB."
    condition     = var.data_format_conversion_parquet_page_size >= 65536
  }
}

variable "data_format_conversion_parquet_writer_version" {
  description = "Indicates the version of row format to output."
  type        = string
  default     = "V1"
  validation {
    error_message = "Valid values are V1 and V2."
    condition     = contains(["V1", "V2"], var.data_format_conversion_parquet_writer_version)
  }
}

variable "data_format_conversion_orc_compression" {
  description = "The compression code to use over data blocks."
  type        = string
  default     = "SNAPPY"
  validation {
    error_message = "Valid values are NONE, ZLIB and SNAPPY."
    condition     = contains(["NONE", "ZLIB", "SNAPPY"], var.data_format_conversion_orc_compression)
  }
}

variable "data_format_conversion_orc_format_version" {
  description = "The version of the file to write."
  type        = string
  default     = "V0_12"
  validation {
    error_message = "Valid values are V0_11 and V0_12."
    condition     = contains(["V0_11", "V0_12"], var.data_format_conversion_orc_format_version)
  }
}

variable "data_format_conversion_orc_enable_padding" {
  description = "Set this to true to indicate that you want stripes to be padded to the HDFS block boundaries. This is useful if you intend to copy the data from Amazon S3 to HDFS before querying."
  type        = bool
  default     = false
}

variable "data_format_conversion_orc_padding_tolerance" {
  description = "A float between 0 and 1 that defines the tolerance for block padding as a decimal fraction of stripe size."
  type        = number
  default     = 0.05
  validation {
    error_message = "Valid values are V0_11 and V0_12."
    condition     = var.data_format_conversion_orc_padding_tolerance >= 0 && var.data_format_conversion_orc_padding_tolerance <= 1
  }
}

variable "data_format_conversion_orc_dict_key_threshold" {
  description = "A float that represents the fraction of the total number of non-null rows. To turn off dictionary encoding, set this fraction to a number that is less than the number of distinct keys in a dictionary. To always use dictionary encoding, set this threshold to 1."
  type        = number
  default     = 0.0
  validation {
    error_message = "Valid values are between 0 and 1."
    condition     = var.data_format_conversion_orc_dict_key_threshold >= 0 && var.data_format_conversion_orc_dict_key_threshold <= 1
  }
}

variable "data_format_conversion_orc_bloom_filter_columns" {
  description = "A list of column names for which you want Kinesis Data Firehose to create bloom filters."
  type        = list(string)
  default     = []
}

variable "data_format_conversion_orc_bloom_filter_false_positive_probability" {
  description = "The Bloom filter false positive probability (FPP). The lower the FPP, the bigger the Bloom filter."
  type        = number
  default     = 0.05
  validation {
    error_message = "Valid values are between 0 and 1."
    condition     = var.data_format_conversion_orc_bloom_filter_false_positive_probability >= 0 && var.data_format_conversion_orc_bloom_filter_false_positive_probability <= 1
  }
}

variable "data_format_conversion_orc_row_index_stripe" {
  description = "The number of rows between index entries."
  type        = number
  default     = 10000
  validation {
    error_message = "Minimum value is 1000."
    condition     = var.data_format_conversion_orc_row_index_stripe >= 1000
  }
}

variable "data_format_conversion_orc_stripe_size" {
  description = "he number of bytes in each strip."
  type        = number
  default     = 67108864
  validation {
    error_message = "Minimum Value is 8 MiB."
    condition     = var.data_format_conversion_orc_stripe_size >= 8388608
  }
}

variable "append_delimiter_to_record" {
  description = "To configure your delivery stream to add a new line delimiter between records in objects that are delivered to Amazon S3."
  type        = bool
  default     = false
}

######
# Redshift Destination Variables
######
variable "redshift_cluster_endpoint" {
  description = "The redshift endpoint"
  type        = string
  default     = null
}

variable "redshift_username" {
  description = "The username that the firehose delivery stream will assume. It is strongly recommended that the username and password provided is used exclusively for Amazon Kinesis Firehose purposes, and that the permissions for the account are restricted for Amazon Redshift INSERT permissions"
  type        = string
  default     = null
  sensitive   = true
}

variable "redshift_password" {
  description = "The password for the redshift username above"
  type        = string
  default     = null
  sensitive   = true
}

variable "redshift_database_name" {
  description = "The redshift database name"
  type        = string
  default     = null
}

variable "redshift_table_name" {
  description = "The name of the table in the redshift cluster that the s3 bucket will copy to"
  type        = string
  default     = null
}

variable "redshift_copy_options" {
  description = "Copy options for copying the data from the s3 intermediate bucket into redshift, for example to change the default delimiter"
  type        = string
  default     = null
}

variable "redshift_data_table_columns" {
  description = "The data table columns that will be targeted by the copy command"
  type        = string
  default     = null
}

variable "redshift_retry_duration" {
  description = "The length of time during which Firehose retries delivery after a failure, starting from the initial request and including the first attempt"
  type        = string
  default     = 3600
  validation {
    error_message = "Minimum: 0 second, maximum: 7200 seconds."
    condition     = var.redshift_retry_duration >= 0 && var.redshift_retry_duration <= 7200
  }
}

variable "redshift_cluster_identifier" {
  description = "Redshift Cluster identifier. Necessary to associate the iam role to cluster"
  type        = string
  default     = null
}

variable "associate_role_to_redshift_cluster" {
  description = "Set it to false if don't want the module associate the role to redshift cluster"
  type        = bool
  default     = true
}

######
# Elasticsearch Destination Variables
######
variable "elasticsearch_domain_arn" {
  description = "The ARN of the Amazon ES domain. The pattern needs to be arn:.*"
  type        = string
  default     = null
}

variable "elasticsearch_index_name" {
  description = "The Elasticsearch index name"
  type        = string
  default     = null
}

variable "elasticsearch_index_rotation_period" {
  description = "The Elasticsearch index rotation period. Index rotation appends a timestamp to the IndexName to facilitate expiration of old data"
  type        = string
  default     = "OneDay"
  validation {
    error_message = "Valid values are NoRotation, OneHour, OneDay, OneWeek, and OneMonth."
    condition     = contains(["NoRotation", "OneHour", "OneDay", "OneWeek", "OneMonth"], var.elasticsearch_index_rotation_period)
  }
}

variable "elasticsearch_type_name" {
  description = "The Elasticsearch type name with maximum length of 100 characters"
  type        = string
  default     = null
}

variable "elasticsearch_retry_duration" {
  description = "The length of time during which Firehose retries delivery after a failure, starting from the initial request and including the first attempt"
  type        = string
  default     = 300
  validation {
    error_message = "Minimum: 0 seconds."
    condition     = var.elasticsearch_retry_duration >= 0 && var.elasticsearch_retry_duration <= 7200
  }
}

######
# Opensearch Destination Variables
######
variable "opensearch_domain_arn" {
  description = "The ARN of the Amazon Opensearch domain. The pattern needs to be arn:.*. Conflicts with cluster_endpoint."
  type        = string
  default     = null
}

variable "opensearch_index_name" {
  description = "The Opensearch (And OpenSearch Serverless) index name."
  type        = string
  default     = null
}

variable "opensearch_index_rotation_period" {
  description = "The Opensearch index rotation period. Index rotation appends a timestamp to the IndexName to facilitate expiration of old data"
  type        = string
  default     = "OneDay"
  validation {
    error_message = "Valid values are NoRotation, OneHour, OneDay, OneWeek, and OneMonth."
    condition     = contains(["NoRotation", "OneHour", "OneDay", "OneWeek", "OneMonth"], var.opensearch_index_rotation_period)
  }
}

variable "opensearch_type_name" {
  description = "The opensearch type name with maximum length of 100 characters. Types are deprecated in OpenSearch_1.1. TypeName must be empty."
  type        = string
  default     = null
}

variable "opensearch_retry_duration" {
  description = "After an initial failure to deliver to Amazon OpenSearch, the total amount of time, in seconds between 0 to 7200, during which Firehose re-attempts delivery (including the first attempt). After this time has elapsed, the failed documents are written to Amazon S3. The default value is 300s. There will be no retry if the value is 0."
  type        = string
  default     = 300
  validation {
    error_message = "Minimum: 0 seconds."
    condition     = var.opensearch_retry_duration >= 0 && var.opensearch_retry_duration <= 7200
  }
}

variable "opensearch_vpc_create_service_linked_role" {
  description = "Set it to True if want create Opensearch Service Linked Role to Access VPC."
  type        = bool
  default     = false
}

variable "opensearch_document_id_options" {
  description = "The method for setting up document ID."
  type        = string
  default     = "FIREHOSE_DEFAULT"
  validation {
    error_message = "Valid values are FIREHOSE_DEFAULT and NO_DOCUMENT_ID."
    condition     = contains(["FIREHOSE_DEFAULT", "NO_DOCUMENT_ID"], var.opensearch_document_id_options)
  }
}

variable "opensearchserverless_collection_endpoint" {
  description = "The endpoint to use when communicating with the collection in the Serverless offering for Amazon OpenSearch Service."
  type        = string
  default     = null
}

variable "opensearchserverless_collection_arn" {
  description = "The ARN of the Amazon Opensearch Serverless Collection. The pattern needs to be arn:.*."
  type        = string
  default     = null
}
######
# VPC Variables
######
variable "enable_vpc" {
  description = "Indicates if destination is configured in VPC. Supports Elasticsearch and Opensearch destinations."
  type        = bool
  default     = false
}

variable "vpc_use_existing_role" {
  description = "Indicates if want use the kinesis firehose role to VPC access. Supports Elasticsearch and Opensearch destinations."
  type        = bool
  default     = true
}

variable "vpc_role_arn" {
  description = "The ARN of the IAM role to be assumed by Firehose for calling the Amazon EC2 configuration API and for creating network interfaces. Supports Elasticsearch and Opensearch destinations."
  type        = string
  default     = null
}

variable "vpc_subnet_ids" {
  description = "A list of subnet IDs to associate with Kinesis Firehose. Supports Elasticsearch and Opensearch destinations."
  type        = list(string)
  default     = null
}

variable "vpc_security_group_same_as_destination" {
  description = "Indicates if the firehose security group is the same as destination."
  type        = bool
  default     = true
}

variable "vpc_security_group_firehose_ids" {
  description = "A list of security group IDs to associate with Kinesis Firehose."
  type        = list(string)
  default     = null
}

variable "vpc_create_security_group" {
  description = "Indicates if want create security group to associate to kinesis firehose"
  type        = bool
  default     = false
}

variable "vpc_security_group_firehose_configure_existing" {
  description = "Indicates if want configure an existing firehose security group with the necessary rules"
  type        = bool
  default     = false
}

variable "vpc_security_group_tags" {
  description = "A map of tags to assign to security group"
  type        = map(string)
  default     = {}
}

variable "vpc_security_group_destination_ids" {
  description = "A list of security group IDs associated to destinations to allow firehose traffic"
  type        = list(string)
  default     = null
}

variable "vpc_create_destination_security_group" {
  description = "Indicates if want create destination security group to associate to firehose destinations"
  type        = bool
  default     = false
}

variable "vpc_security_group_destination_configure_existing" {
  description = "Indicates if want configure an existing destination security group with the necessary rules"
  type        = bool
  default     = false
}

variable "vpc_security_group_destination_vpc_id" {
  description = "VPC ID to create the destination security group. Only supported to Redshift and splunk destinations"
  type        = string
  default     = null
}
######
# Splunk Destination Variables
######
variable "splunk_hec_endpoint" {
  description = "The HTTP Event Collector (HEC) endpoint to which Kinesis Firehose sends your data"
  type        = string
  default     = null
}

variable "splunk_hec_token" {
  description = "The GUID that you obtain from your Splunk cluster when you create a new HEC endpoint"
  type        = string
  default     = null
  sensitive   = true
}

variable "splunk_hec_acknowledgment_timeout" {
  description = "The amount of time, that Kinesis Firehose waits to receive an acknowledgment from Splunk after it sends it data"
  type        = number
  default     = 600
  validation {
    error_message = "Minimum: 180 seconds. maximum: 600 seconds."
    condition     = var.splunk_hec_acknowledgment_timeout >= 180 && var.splunk_hec_acknowledgment_timeout <= 600
  }
}

variable "splunk_hec_endpoint_type" {
  description = " The HEC endpoint type"
  type        = string
  default     = "Raw"
  validation {
    error_message = "Valid values are Raw and Event."
    condition     = contains(["Raw", "Event"], var.splunk_hec_endpoint_type)
  }
}

variable "splunk_retry_duration" {
  description = "After an initial failure to deliver to Splunk, the total amount of time, in seconds between 0 to 7200, during which Firehose re-attempts delivery (including the first attempt)"
  type        = number
  default     = 450
  validation {
    error_message = "Minimum: 0 seconds. Maximum: 7200 seconds."
    condition     = var.splunk_retry_duration >= 0 && var.splunk_retry_duration <= 7200
  }
}

######
# Http Endpoint Destination Variables
######
variable "http_endpoint_url" {
  description = "The HTTP endpoint URL to which Kinesis Firehose sends your data"
  type        = string
  default     = null
}

variable "http_endpoint_name" {
  description = "The HTTP endpoint name"
  type        = string
  default     = null
}

variable "http_endpoint_access_key" {
  description = "The access key required for Kinesis Firehose to authenticate with the HTTP endpoint selected as the destination"
  type        = string
  default     = null
  sensitive   = true
}

variable "http_endpoint_retry_duration" {
  description = "Total amount of seconds Firehose spends on retries. This duration starts after the initial attempt fails, It does not include the time periods during which Firehose waits for acknowledgment from the specified destination after each attempt"
  type        = number
  default     = 300
  validation {
    error_message = "Minimum: 0 seconds. Maximum: 7200 seconds."
    condition     = var.http_endpoint_retry_duration >= 0 && var.http_endpoint_retry_duration <= 7200
  }
}

variable "http_endpoint_enable_request_configuration" {
  description = "The request configuration"
  type        = bool
  default     = false
}

variable "http_endpoint_request_configuration_content_encoding" {
  description = "Kinesis Data Firehose uses the content encoding to compress the body of a request before sending the request to the destination"
  type        = string
  default     = "GZIP"
  validation {
    error_message = "Valid values are GZIP and NONE."
    condition     = contains(["GZIP", "NONE"], var.http_endpoint_request_configuration_content_encoding)
  }
}

variable "http_endpoint_request_configuration_common_attributes" {
  description = "Describes the metadata sent to the HTTP endpoint destination. The variable is list. Each element is map with two keys , name and value, that corresponds to common attribute name and value"
  type        = list(map(string))
  default     = []
}

######
# Datadog Destination Variables
######
variable "datadog_endpoint_type" {
  description = "Endpoint type to datadog destination"
  type        = string
  default     = "logs_eu"
  validation {
    error_message = "Please use a valid endpoint type!"
    condition     = contains(["logs_us", "logs_eu", "logs_gov", "metrics_us", "metrics_eu"], var.datadog_endpoint_type)
  }
}

######
# New Relic Destination Variables
######
variable "newrelic_endpoint_type" {
  description = "Endpoint type to New Relic destination"
  type        = string
  default     = "logs_eu"
  validation {
    error_message = "Please use a valid endpoint type!"
    condition     = contains(["logs_us", "logs_eu", "metrics_us", "metrics_eu"], var.newrelic_endpoint_type)
  }
}

######
# Dynatrace Destination Variables
######
variable "dynatrace_endpoint_location" {
  description = "Endpoint Location to Dynatrace destination"
  type        = string
  default     = "eu"
  validation {
    error_message = "Please use a valid endpoint type!"
    condition     = contains(["us", "eu", "global"], var.dynatrace_endpoint_location)
  }
}

variable "dynatrace_api_url" {
  description = "API URL to Dynatrace destination"
  type        = string
  default     = null
}

######
# Honeycomb Destination Variables
######
variable "honeycomb_api_host" {
  type        = string
  default     = "https://api.honeycomb.io"
  description = "If you use a Secure Tenancy or other proxy, put its schema://host[:port] here"
}

variable "honeycomb_dataset_name" {
  type        = string
  description = "Your Honeycomb dataset name to Honeycomb destination"
  default     = null
}

######
# Logic Monitor Destination Variables
######
variable "logicmonitor_account" {
  type        = string
  description = "Account to use in Logic Monitor destination"
  default     = null
}

######
# MongoDB Destination Variables
######
variable "mongodb_realm_webhook_url" {
  type        = string
  description = "Realm Webhook URL to use in MongoDB destination"
  default     = null
}

######
# SumoLogic Destination Variables
######
variable "sumologic_deployment_name" {
  type        = string
  description = "Deployment Name to use in Sumo Logic destination"
  default     = null
}

variable "sumologic_data_type" {
  type        = string
  description = "Data Type to use in Sumo Logic destination"
  default     = "log"
  validation {
    error_message = "Please use a valid data type!"
    condition     = contains(["log", "metric"], var.sumologic_data_type)
  }
}

######
# Coralogix Destination Variables
######
variable "coralogix_endpoint_location" {
  description = "Endpoint Location to coralogix destination"
  type        = string
  default     = "ireland"
  validation {
    error_message = "Please use a valid endpoint type!"
    condition     = contains(["us", "singapore", "ireland", "india", "stockholm"], var.coralogix_endpoint_location)
  }
}

variable "coralogix_parameter_application_name" {
  description = "By default, your delivery stream arn will be used as applicationName."
  type        = string
  default     = null
}

variable "coralogix_parameter_subsystem_name" {
  description = "By default, your delivery stream name will be used as subsystemName."
  type        = string
  default     = null
}

variable "coralogix_parameter_use_dynamic_values" {
  description = "To use dynamic values for applicationName and subsystemName."
  type        = bool
  default     = false
}

######
# Snowflake Destination Variables
######
variable "snowflake_account_identifier" {
  description = "The Snowflake account identifier."
  type        = string
  default     = null
}

variable "snowflake_private_key" {
  description = "The Snowflake private key for authentication."
  type        = string
  default     = null
  sensitive   = true
}

variable "snowflake_key_passphrase" {
  description = "The Snowflake passphrase for the private key."
  type        = string
  default     = null
  sensitive   = true
}

variable "snowflake_user" {
  description = "The user for authentication.."
  type        = string
  default     = null
}

variable "snowflake_database" {
  description = "The Snowflake database name."
  type        = string
  default     = null
}

variable "snowflake_schema" {
  description = "The Snowflake schema name."
  type        = string
  default     = null
}

variable "snowflake_table" {
  description = "The Snowflake table name."
  type        = string
  default     = null
}

variable "snowflake_data_loading_option" {
  description = "The data loading option."
  type        = string
  default     = null
  validation {
    error_message = "Please use a valid data loading option!"
    condition     = var.snowflake_data_loading_option == null || contains(["JSON_MAPPING", "VARIANT_CONTENT_MAPPING", "VARIANT_CONTENT_AND_METADATA_MAPPING"], coalesce(var.snowflake_data_loading_option, "dummy"))
  }
}

variable "snowflake_metadata_column_name" {
  description = "The name of the metadata column."
  type        = string
  default     = null
}

variable "snowflake_content_column_name" {
  description = "The name of the content column."
  type        = string
  default     = null
}

variable "snowflake_private_link_vpce_id" {
  description = "The VPCE ID for Firehose to privately connect with Snowflake."
  type        = string
  default     = null
}

variable "snowflake_role_configuration_enabled" {
  description = "Whether the Snowflake role is enabled."
  type        = bool
  default     = false
}

variable "snowflake_role_configuration_role" {
  description = "The Snowflake role."
  type        = string
  default     = null
}

variable "snowflake_retry_duration" {
  description = "The length of time during which Firehose retries delivery after a failure, starting from the initial request and including the first attempt."
  type        = string
  default     = 60
  validation {
    error_message = "Minimum: 0 second, maximum: 7200 seconds."
    condition     = var.snowflake_retry_duration >= 0 && var.snowflake_retry_duration <= 7200
  }
}

######
# Secrets Manager
######
variable "enable_secrets_manager" {
  description = "Enables or disables the Secrets Manager configuration."
  type        = bool
  default     = false
}

variable "secret_arn" {
  description = "The ARN of the Secrets Manager secret. This value is required if enable_secrets_manager is true."
  type        = string
  default     = null
}

variable "secret_kms_key_arn" {
  description = "The ARN of the KMS Key to encrypt the Secret. This value is required if key used to encrypt the Secret is CMK and want the module generates the IAM Policy to access it."
  type        = string
  default     = null
}

######
# IAM
######
variable "firehose_role" {
  description = "IAM role ARN attached to the Kinesis Firehose Stream."
  type        = string
  default     = null
}

variable "role_name" {
  description = "Name of IAM role to use for Kinesis Firehose Stream"
  type        = string
  default     = null
}

variable "role_description" {
  description = "Description of IAM role to use for Kinesis Firehose Stream"
  type        = string
  default     = null
}

variable "role_path" {
  description = "Path of IAM role to use for Kinesis Firehose Stream"
  type        = string
  default     = null
}

variable "role_force_detach_policies" {
  description = "Specifies to force detaching any policies the IAM role has before destroying it"
  type        = bool
  default     = true
}

variable "role_permissions_boundary" {
  description = "The ARN of the policy that is used to set the permissions boundary for the IAM role used by Kinesis Firehose Stream"
  type        = string
  default     = null
}

variable "role_tags" {
  description = "A map of tags to assign to IAM role"
  type        = map(string)
  default     = {}
}

variable "policy_path" {
  description = "Path of policies to that should be added to IAM role for Kinesis Firehose Stream"
  type        = string
  default     = null
}

variable "create_application_role" {
  description = "Set it to true to create role to be used by the source"
  default     = false
  type        = bool
}

variable "application_role_name" {
  description = "Name of IAM Application role to use for Kinesis Firehose Stream Source"
  type        = string
  default     = null
}

variable "application_role_description" {
  description = "Description of IAM Application role to use for Kinesis Firehose Stream Source"
  type        = string
  default     = null
}

variable "application_role_path" {
  description = "Path of IAM Application role to use for Kinesis Firehose Stream Source"
  type        = string
  default     = null
}

variable "application_role_force_detach_policies" {
  description = "Specifies to force detaching any policies the IAM Application role has before destroying it"
  type        = bool
  default     = true
}

variable "application_role_permissions_boundary" {
  description = "The ARN of the policy that is used to set the permissions boundary for the IAM Application role used by Kinesis Firehose Stream Source"
  type        = string
  default     = null
}

variable "application_role_tags" {
  description = "A map of tags to assign to IAM Application role"
  type        = map(string)
  default     = {}
}

variable "configure_existing_application_role" {
  description = "Set it to True if want use existing application role to add the firehose Policy"
  default     = false
  type        = bool
}

variable "create_application_role_policy" {
  description = "Set it to true to create policy to the role used by the source"
  default     = false
  type        = bool
}

variable "application_role_service_principal" {
  description = "AWS Service Principal to assume application role"
  type        = string
  default     = null
}

variable "application_role_policy_actions" {
  description = "List of Actions to Application Role Policy"
  type        = list(string)
  default = [
    "firehose:PutRecord",
    "firehose:PutRecordBatch"
  ]
}

variable "general" {}
