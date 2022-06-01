
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

data "amazon-ami" "windows" {
  filters = {
    name                = "Windows_Server-2016-English-Full-Base-*"
    root-device-type    = "ebs"
    virtualization-type = "hvm"
  }
  most_recent = true
  owners      = ["801119661308"]
}

source "amazon-ebs" "windows" {
  ami_name              = "windows-2016-${replace(var.version, ".", "-")}"
  force_delete_snapshot = "true"
  force_deregister      = "true"
  instance_type         = "t3.xlarge"
  source_ami            = "${data.amazon-ami.windows.id}"
  user_data_file        = "windows_server/bootstrap_win_winrm_https.txt"
  communicator          = "winrm"
  winrm_username        = "Administrator"
  winrm_insecure        = true
  winrm_use_ssl         = true
}

source "azure-arm" "windows" {
  managed_image_resource_group_name = "packer"
  managed_image_name = "windows-2016-${replace(var.version, ".", "-")}"
  subscription_id = "adf9dc10-01d2-4d80-99ff-5c90142e6293"
  os_type = "Windows"
  image_publisher = "MicrosoftWindowsServer"
  image_offer = "WindowsServer"
  image_sku = "2016-Datacenter"
  location = "West Europe"
  vm_size = "Standard_D4_v4"
  communicator = "winrm"
  winrm_insecure = true
  winrm_use_ssl = true
  winrm_username = "packer"
  winrm_port = 5986
}

build {

  sources = [
    "source.amazon-ebs.windows",
    "source.azure-arm.windows",
  ]

  provisioner "ansible" {
    only = ["amazon-ebs.windows"]
    playbook_file = "ansible/windows.yml"
    user = "Administrator"
    use_proxy = false
    local_port = 5986
    ansible_env_vars = ["no_proxy=\"*\""]
    extra_arguments = ["--extra-vars", "ansible_shell_type=powershell ansible_shell_executable=None ansible_user=Administrator ansible_password=${var.win_password} ansible_become_pass={{.WinRMPassword}} splunk_uf_win_url=${var.splunk_uf_win_url} splunk_admin_password=${var.splunk_admin_password}"]
  }

  provisioner "powershell" {
    only = ["azure-arm.windows"]
    script = "windows_server/AnsibleSetup.ps1"
  }

  provisioner "ansible" {
    only = ["azure-arm.windows"]
    playbook_file = "ansible/windows.yml"
    user = "packer"
    use_proxy = false
    local_port = 5986
    ansible_env_vars = ["WINRM_PASSWORD={{.WinRMPassword}}", "no_proxy=\"*\""]
    extra_arguments = ["--extra-vars", "ansible_winrm_operation_timeout_sec=120 ansible_winrm_read_timeout_sec=150 ansible_shell_type=powershell ansible_shell_executable=None ansible_become_pass={{.WinRMPassword}} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} splunk_admin_password=${var.splunk_admin_password}"]
  }

  provisioner "powershell" {
    only = ["azure-arm.windows"]
    script = "windows_server/sysprep.ps1"
  }

  provisioner "powershell" {
    only = ["amazon-ebs.windows"]
    inline = [
      "C:/ProgramData/Amazon/EC2-Windows/Launch/Scripts/InitializeInstance.ps1 -Schedule",
      "C:/ProgramData/Amazon/EC2-Windows/Launch/Scripts/SysprepInstance.ps1"
    ]
  }

}