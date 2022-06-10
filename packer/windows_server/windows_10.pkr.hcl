
variable "splunk_admin_password" {
  type    = string
  default = "Pl3ase-k1Ll-me:p"
}

variable "splunk_uf_win_url" {
  type    = string
  default = "https://download.splunk.com/products/universalforwarder/releases/8.2.5/windows/splunkforwarder-8.2.5-77015bc7a462-x64-release.msi"
}

variable "win_password" {
  type    = string
  default = "Pl3ase-k1Ll-me:p"
}

variable "version" {
  type    = string
  default = "2.0.0"
}

variable "location_azure" {
  type    = string
  default = "West Europe"
}


source "azure-arm" "windows" {
  managed_image_resource_group_name = "packer_${replace(var.location_azure, " ", "_")}"
  managed_image_name = "windows-10-${replace(var.version, ".", "-")}"
  subscription_id = "adf9dc10-01d2-4d80-99ff-5c90142e6293"
  os_type = "Windows"
  image_publisher = "microsoftwindowsdesktop"
  image_offer = "windows-10"
  image_sku = "win10-21h2-pro"
  location = var.location_azure
  vm_size = "Standard_D4_v4"
  communicator = "winrm"
  winrm_insecure = true
  winrm_use_ssl = true
  winrm_username = "packer"
  winrm_port = 5986
}

build {

  sources = [
    "source.azure-arm.windows"
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
    extra_arguments = ["--extra-vars", "ansible_winrm_operation_timeout_sec=120 ansible_winrm_read_timeout_sec=150 ansible_shell_type=powershell ansible_shell_executable=None ansible_become_pass={{.WinRMPassword}} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} splunk_admin_password=${var.splunk_admin_password}"]
  }

  provisioner "powershell" {
    only = ["azure-arm.windows"]
    script = "packer/windows_server/sysprep.ps1"
  }

}