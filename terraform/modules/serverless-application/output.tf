output "api_gateway_id" {
  value = "${aws_api_gateway_rest_api.example[0].id}"
}

output "db_id" {
  value = "${aws_db_instance.db_attack_range[0].resource_id}"
}
