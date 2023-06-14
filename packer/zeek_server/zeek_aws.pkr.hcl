
variable "general" {
    type = map(string)

    default = {
        attack_range_password = "Pl3ase-k1Ll-me:p"
        key_name = "attack-range-key-pair"
        attack_range_name = "ar"
        ip_whitelist = "0.0.0.0/0"
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
    name                = "*ubuntu-focal-20.04-amd64-server-*"
    root-device-type    = "ebs"
    virtualization-type = "hvm"
  }
  most_recent = true
  owners      = ["099720109477"]
}

source "amazon-ebs" "ubuntu" {
  ami_name              = "zeek-v${replace(var.general.version, ".", "-")}"
  region = var.aws.region
  instance_type         = "t3.xlarge"
  launch_block_device_mappings {
    device_name = "/dev/sda1"
    volume_size = "30"
  }
  source_ami   = "${data.amazon-ami.ubuntu-ami.id}"
  ssh_username = "ubuntu"
  force_deregister = true
  force_delete_snapshot = true
}

build {

  sources = [
    "source.amazon-ebs.ubuntu"
  ]

  provisioner "ansible" {
    extra_arguments = ["--scp-extra-args", "'-O'", "--extra-vars", "${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])}"]
    playbook_file   = "packer/ansible/zeek.yml"
    user            = "ubuntu"
    ansible_ssh_extra_args = ["-oHostKeyAlgorithms=+ssh-rsa -oPubkeyAcceptedKeyTypes=+ssh-rsa"]
  }

}
