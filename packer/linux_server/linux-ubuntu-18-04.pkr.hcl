
variable "general" {
    type = map(string)

    default = {
        attack_range_password = "Pl3ase-k1Ll-me:p"
        key_name = "attack-range-key-pair"
        attack_range_name = "ar"
        ip_whitelist = "0.0.0.0/0"
    }
}

variable "azure" {
    type = map(string)

    default = {
        location = "West Europe"
        private_key_path = "~/.ssh/id_rsa"
        public_key_path = "~/.ssh/id_rsa.pub"
    }
}

variable "aws" {
    type = map(string)

    default = {
        region = "eu-central-1"
        private_key_path = "~/.ssh/id_rsa"
        image_owner = "591511147606"
    }
}

variable "splunk_server" {
    type = map(string)

    default = {
        install_es = "0"
        splunk_es_app = "splunk-enterprise-security_701.spl"
    }
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
  ami_name              = "linux-v${replace(var.general.version, ".", "-")}"
  ami_regions           = ["eu-central-1", "us-west-2", "us-west-1", "us-east-2"]
  region                = var.aws.region
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

source "azure-arm" "ubuntu-18-04" {
  managed_image_resource_group_name = "packer_${replace(var.azure.location, " ", "_")}"
  managed_image_name = "linux-v${replace(var.general.version, ".", "-")}"
  os_type = "Linux"
  image_publisher = "Canonical"
  image_offer = "UbuntuServer"
  image_sku = "18.04-LTS"
  location = var.azure.location
  vm_size = "Standard_A4_v2"
  use_azure_cli_auth = true
}

build {

  sources = [
    "source.azure-arm.ubuntu-18-04",
    "source.amazon-ebs.ubuntu-18-04"
  ]

  provisioner "ansible" {
    extra_arguments = ["--extra-vars", "${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])}"]
    playbook_file   = "packer/ansible/linux_server.yml"
  }

}
