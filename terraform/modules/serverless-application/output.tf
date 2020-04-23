output "api_gateway_id" {
  value = "${aws_api_gateway_rest_api.example[0].id}"
}

output "sqs_queue_url" {
  value = "${aws_sqs_queue.queue[0].id}"
}
