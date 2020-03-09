
output "phantom_server_instance" {
  value = "${aws_instance.phantom-server}"
}

output "phantom_server_instance_packer" {
  value = "${aws_instance.phantom-server-packer}"
}
