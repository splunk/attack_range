
locals {
    custom_data_content  = file("${path.module}/files/winrm.ps1")
}

resource "azurerm_network_interface" "windows-nic" {
  count = length(var.windows_servers)
  name = "ar-windows-nic-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location = var.azure.region
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
  location            = var.azure.region
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

data "azurerm_image" "search" {
  count = length(var.windows_servers) > 0 ? 1 : 0
  name                = var.windows_servers[count.index].image
  resource_group_name = "packer"
}

resource "azurerm_virtual_machine" "windows" {
  count = length(var.windows_servers)
  name = "ar-win-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location = var.azure.region
  resource_group_name   = var.rg_name
  network_interface_ids = [azurerm_network_interface.windows-nic[count.index].id]
  vm_size               = "Standard_D4_v4"

  delete_os_disk_on_termination = true

  storage_image_reference {
    id = data.azurerm_image.search[0].id
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
    command = "ansible-playbook -i '${azurerm_public_ip.windows-publicip[count.index].ip_address},' windows_post.yml --extra-vars 'ansible_port=5985 ansible_user=AzureAdmin ansible_password=${var.general.attack_range_password} ansible_winrm_operation_timeout_sec=120 ansible_winrm_read_timeout_sec=150 attack_range_password=${var.general.attack_range_password} ${join(" ", [for key, value in var.windows_servers[count.index] : "${key}=\"${value}\""])}'"
  }

}