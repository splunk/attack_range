
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

variable "splunk_server" {
    type = map(string)

    default = {
        install_es = "0"
        splunk_es_app = "splunk-enterprise-security_701.spl"
    }
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
    "source.azure-arm.ubuntu-18-04"
  ]

  provisioner "ansible" {
    extra_arguments = ["--extra-vars", "${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])}"]
    playbook_file   = "packer/ansible/linux_server.yml"
    user            = "ubuntu"
  }

}
