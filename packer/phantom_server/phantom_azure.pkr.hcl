
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

variable "phantom_server" {
    type = map(string)
    default = {
        phantom_server = "0"
        phantom_community_username = "user"
        phantom_community_password = "password"
        phantom_repo_url = "https://repo.phantom.us/phantom/5.2/base/7/x86_64/phantom_repo-5.2.1.78411-1.x86_64.rpm"
        phantom_version = "5.2.1.78411-1"
    }
}

variable "splunk_server" {
    type = map(string)

    default = {
        install_es = "0"
        splunk_es_app = "splunk-enterprise-security_701.spl"
    }
}

source "azure-arm" "phantom" {
  managed_image_resource_group_name = "packer_${replace(var.azure.location, " ", "_")}"
  managed_image_name = "phantom-v${replace(var.general.version, ".", "-")}"
  os_type = "Linux"
  image_publisher = "openlogic"
  image_offer = "centos"
  image_sku = "7_9"
  location = var.azure.location
  vm_size = "Standard_A8_v2"
  use_azure_cli_auth = true
}

build {

  sources = [
    "source.azure-arm.phantom"
  ]

  provisioner "ansible" {
    extra_arguments = ["--extra-vars", "${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.phantom_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])}"]
    playbook_file   = "packer/ansible/phantom_server.yml"
    user            = "centos"
  }

}
