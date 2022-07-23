
variable "splunk_admin_password" {
  type    = string
  default = "Pl3ase-k1Ll-me:p"
}

variable "splunk_uf_url" {
  type    = string
  default = "https://download.splunk.com/products/universalforwarder/releases/8.2.5/linux/splunkforwarder-8.2.5-77015bc7a462-linux-2.6-amd64.deb"
}

variable "version" {
  type    = string
  default = "3.0.0"
}

variable "location_azure" {
  type    = string
  default = "West Europe"
}

data "amazon-ami" "ubuntu-ami" {
  filters = {
    name                = "*ubuntu-bionic-18.04-amd64-server-*"
    root-device-type    = "ebs"
    virtualization-type = "hvm"
  }
  most_recent = true
  owners      = ["099720109477"]
}

source "amazon-ebs" "ubuntu-18-04" {
  ami_name              = "zeek-v${replace(var.version, ".", "-")}"
  instance_type         = "t3.xlarge"
  launch_block_device_mappings {
    device_name = "/dev/sda1"
    volume_size = "50"
  }
  source_ami   = "${data.amazon-ami.ubuntu-ami.id}"
  ssh_username = "ubuntu"
  force_deregister = true
  force_delete_snapshot = true
}

build {

  sources = [
    "source.amazon-ebs.ubuntu-18-04"
  ]

  provisioner "ansible" {
    extra_arguments = ["--extra-vars", "splunk_uf_url=${var.splunk_uf_url}"]
    playbook_file   = "packer/ansible/zeek.yml"
  }

}
