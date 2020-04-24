output "api_gateway_id" {
  value = var.cloud_attack_range == "1" ? aws_api_gateway_rest_api.example[0].id : "false"
}

output "sqs_queue_url" {
  value = var.cloud_attack_range == "1" && var.cloudtrail=="1" ? aws_sqs_queue.queue[0].id : "false"
}
