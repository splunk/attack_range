variable "waf_prefix" {
  type        = string
  description = "Prefix to use when naming resources"
}

variable "blacklisted_ips" {
  type        = list(string)
  default     = []
  description = "List of IPs to blacklist, eg ['1.1.1.1/32', '2.2.2.2/32', '3.3.3.3/32']"
}

variable "admin_remote_ipset" {
  type        = list(string)
  default     = []
  description = "List of IPs allowed to access admin pages, ['1.1.1.1/32', '2.2.2.2/32', '3.3.3.3/32']"
}

variable "resource_arn" {
  type        = list(string)
  default     = []
  description = "List of ARNs of the resource to associate with"
}

variable "rule_sqli_action" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_auth_tokens_action" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_xss_action" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_lfi_rfi_action" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_admin_access_action_type" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_admin_path_constraints" {
  type        = list(object({ target_string = string, positional_constraint = string }))
  default     = [{ target_string = "/admin", positional_constraint = "STARTS_WITH" }]
  description = "Customize which paths are considered to be admin paths."
}

variable "rule_php_insecurities_action_type" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_size_restriction_action_type" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_csrf_action_type" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_csrf_exclude_methods" {
  type        = list(string)
  default     = ["get", "head", "options"]
  description = "HTTP methods to exclude from CSRF checks (if using include, leave this empty)"
}

variable "rule_csrf_include_methods" {
  type        = list(string)
  default     = []
  description = "HTTP methods to include in CSRF checks (if using exclude, leave this empty)"
}

variable "rule_csrf_header" {
  type        = string
  description = "The name of your CSRF token header."
  default     = "x-csrf-token"
}

variable "rule_ssi_action_type" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "rule_blacklisted_ips_action_type" {
  type        = string
  default     = "COUNT"
  description = "Rule action type. Either BLOCK, ALLOW, or COUNT (useful for testing)"
}

variable "enable_logging" {
  type        = bool
  default     = false
  description = "Enables logging for the WAF"
}

variable "log_destination_arn" {
  type        = string
  default     = ""
  description = "Amazon Resource Name (ARN) of Kinesis Firehose Delivery Stream"
}

variable "log_redacted_fields" {
  type        = list(object({ type = string, data = string }))
  default     = []
  description = "Amazon Resource Name (ARN) of Kinesis Firehose Delivery Stream"
}

variable "tags" {
  type        = map(string)
  description = "A mapping of tags to assign to all resources"
  default     = {}
}

variable "custom_csrf_token" {
  description = "Custom CSRF token set"
  default     = []
}