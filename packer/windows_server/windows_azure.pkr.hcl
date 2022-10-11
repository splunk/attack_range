
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

variable "images" {
  type = map(string)

  default = {
        aws_image = "Windows_Server-2016-English-Full-Base-*"
        azure_publisher = "MicrosoftWindowsServer"
        azure_offer = "WindowsServer"
        azure_sku = "2016-Datacenter"
        name = "windows-2016"
  }
}

source "azure-arm" "windows" {
  managed_image_resource_group_name = "packer_${replace(var.azure.location, " ", "_")}"
  managed_image_name = "${var.images.name}-v${replace(var.general.version, ".", "-")}"
  os_type = "Windows"
  image_publisher = var.images.azure_publisher
  image_offer = var.images.azure_offer
  image_sku = var.images.azure_sku
  location = var.azure.location
  vm_size = "Standard_D4_v4"
  communicator = "winrm"
  winrm_insecure = true
  winrm_use_ssl = true
  winrm_username = "packer"
  winrm_port = 5986
  use_azure_cli_auth = true
}

build {

  sources = [
    "source.azure-arm.windows",
  ]

  provisioner "powershell" {
    only = ["azure-arm.windows"]
    script = "packer/windows_server/AnsibleSetup.ps1"
  }

  provisioner "ansible" {
    only = ["azure-arm.windows"]
    playbook_file = "packer/ansible/windows.yml"
    user = "packer"
    use_proxy = false
    local_port = 5986
    ansible_env_vars = ["WINRM_PASSWORD={{.WinRMPassword}}", "no_proxy=\"*\""]
    extra_arguments = ["--extra-vars", "ansible_winrm_operation_timeout_sec=120 ansible_winrm_read_timeout_sec=150 ansible_shell_type=powershell ansible_shell_executable=None ansible_become_pass={{.WinRMPassword}} ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])}"]
  }

  provisioner "powershell" {
    only = ["azure-arm.windows"]
    script = "packer/windows_server/sysprep.ps1"
  }

}