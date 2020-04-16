output "api_gateway_id" {
  value = "${aws_api_gateway_rest_api.example[0].id}"
}
