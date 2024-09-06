output "web_acl_id" {
  description = "AWS WAF web acl id."
  value       = aws_wafregional_web_acl.wafregional_acl.id
}

output "web_acl_name" {
  description = "The name or description of the web ACL."
  value       = aws_wafregional_web_acl.wafregional_acl.name
}

output "web_acl_metric_name" {
  description = "The name or description for the Amazon CloudWatch metric of this web ACL."
  value       = aws_wafregional_web_acl.wafregional_acl.metric_name
}