
locals {
    custom_data_content  = file("${path.module}/files/winrm.ps1")
}

resource "azurerm_network_interface" "windows-nic" {
  count = length(var.windows_servers)
  name = "ar-windows-nic-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location = var.azure.location
  resource_group_name  = var.rg_name

  ip_configuration {
    name                          = "ar-windows-nic-conf-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.0.1.${14 + count.index}"
    public_ip_address_id          = azurerm_public_ip.windows-publicip[count.index].id
  }
}

resource "azurerm_public_ip" "windows-publicip" {
  count       = length(var.windows_servers)
  name                = "ar-windows-ip-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location            = var.azure.location
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_virtual_machine" "windows" {
  count = length(var.windows_servers)
  name = "ar-win-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location = var.azure.location
  resource_group_name   = var.rg_name
  network_interface_ids = [azurerm_network_interface.windows-nic[count.index].id]
  vm_size               = "Standard_D4_v4"

  delete_os_disk_on_termination = true

  storage_image_reference {
    publisher = var.windows_servers[count.index].azure_publisher 
    offer     = var.windows_servers[count.index].azure_offer
    sku       = var.windows_servers[count.index].azure_sku
    version   = "latest"
  }

  os_profile {
    computer_name  = var.windows_servers[count.index].hostname
    admin_username = "AzureAdmin"
    admin_password = var.general.attack_range_password
    custom_data    = local.custom_data_content
  }

  os_profile_windows_config {
    provision_vm_agent        = true
    enable_automatic_upgrades = false

    additional_unattend_config {
        pass         = "oobeSystem"
        component    = "Microsoft-Windows-Shell-Setup"
        setting_name = "AutoLogon"
        content      = "<AutoLogon><Password><Value>${var.general.attack_range_password}</Value></Password><Enabled>true</Enabled><LogonCount>1</LogonCount><Username>AzureAdmin</Username></AutoLogon>"
    }

    #     # Unattend config is to enable basic auth in WinRM, required for the provisioner stage.
    #     # https://github.com/terraform-providers/terraform-provider-azurerm/blob/master/examples/virtual-machines/provisioners/windows/files/FirstLogonCommands.xml
    additional_unattend_config {
        pass         = "oobeSystem"
        component    = "Microsoft-Windows-Shell-Setup"
        setting_name = "FirstLogonCommands"
        content      = file("${path.module}/files/FirstLogonCommands.xml")
    }
  }

  storage_os_disk {
    name              = "disk-windows-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type     = "winrm"
      user     = "AzureAdmin"
      password = var.general.attack_range_password
      host     = azurerm_public_ip.windows-publicip[count.index].ip_address
      port     = 5985
      insecure = true
      https    = false
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      cat <<EOF > vars/windows_vars_${count.index}.json
      {
        "ansible_user": "AzureAdmin",
        "ansible_port": 5985,
        "ansible_password": ${var.general.attack_range_password},
        "attack_range_password": ${var.general.attack_range_password},
        "general": ${jsonencode(var.general)},
        "splunk_server": ${jsonencode(var.splunk_server)},
        "simulation": ${jsonencode(var.simulation)},
        "windows_servers": ${jsonencode(var.windows_servers[count.index])},
      }
      EOF
    EOT
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${azurerm_public_ip.windows-publicip[count.index].ip_address},' windows.yml -e @vars/windows_vars_${count.index}.json"
  }

}