
locals {
    custom_data_content  = file("${path.module}/files/winrm.ps1")
}

resource "azurerm_network_interface" "win-server-nic" {
  count       = var.config.windows_server == "1" ? 1 : 0
  name = "ar-win-server-nic-${var.config.range_name}-${var.config.key_name}"
  location = var.config.region
  resource_group_name  = var.rg_name

  ip_configuration {
    name                          = "ar-win-server-nic-conf--${var.config.range_name}-${var.config.key_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.config.windows_server_private_ip
    public_ip_address_id          = azurerm_public_ip.win-server-publicip[count.index].id
  }
}

resource "azurerm_public_ip" "win-server-publicip" {
  count       = var.config.windows_server == "1" ? 1 : 0
  name                = "ar-win-server-ip-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}


resource "azurerm_virtual_machine" "win-server" {
  count       = var.config.windows_server == "1" ? 1 : 0
  name = "ar-win-server-${var.config.range_name}-${var.config.key_name}"
  location = var.config.region
  resource_group_name   = var.rg_name
  network_interface_ids = [azurerm_network_interface.win-server-nic[count.index].id]
  vm_size               = var.config.instance_type_vms
  depends_on             = [var.windows_domain_controller_instance]

  delete_os_disk_on_termination = true

  storage_image_reference {
    publisher = "MicrosoftWindowsServer"
    offer     = "WindowsServer"
    sku       = "2016-Datacenter"
    version   = "latest"
  }

  os_profile {
    computer_name  = "win-server"
    admin_username = "AzureAdmin"
    admin_password = var.config.attack_range_password
    custom_data    = local.custom_data_content
  }

  os_profile_windows_config {
    provision_vm_agent        = true
    enable_automatic_upgrades = false

    additional_unattend_config {
      pass         = "oobeSystem"
      component    = "Microsoft-Windows-Shell-Setup"
      setting_name = "AutoLogon"
      content      = "<AutoLogon><Password><Value>${var.config.attack_range_password}</Value></Password><Enabled>true</Enabled><LogonCount>1</LogonCount><Username>AzureAdmin</Username></AutoLogon>"
    }

    # Unattend config is to enable basic auth in WinRM, required for the provisioner stage.
    # https://github.com/terraform-providers/terraform-provider-azurerm/blob/master/examples/virtual-machines/provisioners/windows/files/FirstLogonCommands.xml
    additional_unattend_config {
      pass         = "oobeSystem"
      component    = "Microsoft-Windows-Shell-Setup"
      setting_name = "FirstLogonCommands"
      content      = file("${path.module}/files/FirstLogonCommands.xml")
    }
  }

  storage_os_disk {
    name              = "disk-win-server-${var.config.range_name}-${var.config.key_name}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type     = "winrm"
      user     = "AzureAdmin"
      password = var.config.attack_range_password
      host     = azurerm_public_ip.win-server-publicip[count.index].ip_address
      port     = 5985
      insecure = true
      https    = false
    }
  }

  provisioner "local-exec" {
    working_dir = "../../ansible"
    command = "ansible-playbook -i '${azurerm_public_ip.win-server-publicip[count.index].ip_address},' playbooks/windows_dc_client.yml --extra-vars 'ansible_port=5985 splunk_indexer_ip=${var.config.splunk_server_private_ip} ansible_user=AzureAdmin ansible_password=${var.config.attack_range_password} win_password=${var.config.attack_range_password} splunk_uf_win_url=${var.config.splunk_uf_win_url} win_sysmon_url=${var.config.win_sysmon_url} win_sysmon_template=${var.config.win_sysmon_template} splunk_admin_password=${var.config.attack_range_password} windows_domain_controller_private_ip=${var.config.windows_domain_controller_private_ip} windows_server_join_domain=${var.config.windows_server_join_domain} splunk_stream_app=${var.config.splunk_stream_app} s3_bucket_url=${var.config.s3_bucket_url} win_4688_cmd_line=${var.config.win_4688_cmd_line} verbose_win_security_logging=${var.config.verbose_win_security_logging}'"
  }

}
