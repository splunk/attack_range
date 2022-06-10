
variable "splunk_uf_url" {
  type    = string
  default = "https://download.splunk.com/products/universalforwarder/releases/8.2.5/linux/splunkforwarder-8.2.5-77015bc7a462-linux-2.6-amd64.deb"
}

variable "version" {
  type    = string
  default = "2.0.0"
}

data "amazon-ami" "nginx-ami" {
  filters = {
    name                = "nginx-plus-app-protect-ubuntu-18.04-v2.4-x86_64-developer*"
    root-device-type    = "ebs"
    virtualization-type = "hvm"
  }
  most_recent = true
  owners      = ["679593333241"]
}

source "amazon-ebs" "nginx-web-proxy" {
  ami_name              = "nginx-web-proxy-v${replace(var.version, ".", "-")}"
  instance_type         = "t3.small"
  launch_block_device_mappings {
    device_name = "/dev/sda1"
    volume_size = "20"
  }
  source_ami   = "${data.amazon-ami.nginx-ami.id}"
  ssh_username = "ubuntu"
  force_deregister = true
  force_delete_snapshot = true
}

build {

  sources = [
    "source.amazon-ebs.nginx-web-proxy"
  ]

  provisioner "ansible" {
    extra_arguments = ["--extra-vars", "splunk_uf_url=${var.splunk_uf_url}"]
    playbook_file   = "packer/ansible/nginx_web_proxy.yml"
  }

}