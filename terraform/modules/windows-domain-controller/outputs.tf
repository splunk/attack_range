
output "windows_domain_controller_instance" {
  value = "${aws_instance.windows_domain_controller}"
}

output "windows_domain_controller_instance_packer" {
  value = "${aws_instance.windows_domain_controller_packer}"
}
