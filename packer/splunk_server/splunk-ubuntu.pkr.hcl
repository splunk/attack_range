
variable "s3_bucket_url" {
  type    = string
  default = "https://attack-range-appbinaries.s3-us-west-2.amazonaws.com"
}

variable "splunk_admin_password" {
  type    = string
  default = "Pl3ase-k1Ll-me:p"
}

variable "splunk_url" {
  type    = string
  default = "https://download.splunk.com/products/splunk/releases/8.2.5/linux/splunk-8.2.5-77015bc7a462-Linux-x86_64.tgz"
}

variable "splunk_version" {
  type    = string
  default = "8.2.5"
}

variable "version" {
  type    = string
  default = "2.0.0"
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

source "amazon-ebs" "splunk-ubuntu-18-04" {
  ami_name              = "splunk-${replace(var.splunk_version, ".", "-")}-v${replace(var.version, ".", "-")}"
  instance_type         = "t3.2xlarge"
  launch_block_device_mappings {
    device_name = "/dev/sda1"
    volume_size = "50"
  }
  source_ami   = "${data.amazon-ami.ubuntu-ami.id}"
  ssh_username = "ubuntu"
  force_deregister = true
  force_delete_snapshot = true
}

source "azure-arm" "splunk-ubuntu-18-04" {
  managed_image_resource_group_name = "packer"
  managed_image_name = "splunk-${replace(var.splunk_version, ".", "-")}-v${replace(var.version, ".", "-")}"
  subscription_id = "adf9dc10-01d2-4d80-99ff-5c90142e6293"
  os_type = "Linux"
  image_publisher = "Canonical"
  image_offer = "UbuntuServer"
  image_sku = "18.04-LTS"
  location = "West Europe"
  vm_size = "Standard_A8_v2"
}

build {

  sources = [
    "source.azure-arm.splunk-ubuntu-18-04",
    "source.amazon-ebs.splunk-ubuntu-18-04"
  ]

  provisioner "ansible" {
    extra_arguments = ["--extra-vars", "splunk_admin_password=${var.splunk_admin_password} splunk_url=${var.splunk_url} s3_bucket_url=${var.s3_bucket_url}"]
    playbook_file   = "ansible/splunk_server.yml"
  }

}
