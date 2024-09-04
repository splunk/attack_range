output "arn" {
  description = "The ARN of the hosted zone"
  value       = try(aws_route53_zone.private[0].arn, data.aws_route53_zone.existing.arn)
}
