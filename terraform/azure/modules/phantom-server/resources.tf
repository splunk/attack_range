
resource "azurerm_public_ip" "phantom-publicip" {
  count       = var.config.phantom_server == "1" ? 1 : 0
  name                = "ar-phantom-ip-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "phantom-nic" {
  count       = var.config.phantom_server == "1" ? 1 : 0
  name                = "ar-phantom-nic-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-phantom-nic-conf--${var.config.range_name}-${var.config.key_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.config.phantom_server_private_ip
    public_ip_address_id          = azurerm_public_ip.phantom-publicip[count.index].id
  }
}

resource "azurerm_virtual_machine" "phantom" {
  count       = var.config.phantom_server == "1" ? 1 : 0
  name = "ar-phantom-${var.config.range_name}-${var.config.key_name}"
  location = var.config.region
  resource_group_name  = var.rg_name
  network_interface_ids = [azurerm_network_interface.phantom-nic[count.index].id]
  vm_size               = var.config.instance_type_vms

  delete_os_disk_on_termination = true

  storage_os_disk {
    name              = "disk-phantom-${var.config.range_name}-${var.config.key_name}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  storage_image_reference {
    publisher = "OpenLogic"
    offer     = "CentOS"
    sku       = "7.6"
    version   = "latest"
  }

  os_profile {
    computer_name  = "azure-${var.config.range_name}-phantom"
    admin_username = "centos"
    admin_password = var.config.attack_range_password
  }

  os_profile_linux_config {
    disable_password_authentication = true
    ssh_keys {
      path     = "/home/centos/.ssh/authorized_keys"
      key_data = file(var.config.public_key_path)
    }
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "centos"
      host        = azurerm_public_ip.phantom-publicip[count.index].ip_address
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../ansible/"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u centos --private-key ${var.config.private_key_path} -i '${azurerm_public_ip.phantom-publicip[0].ip_address},' playbooks/phantom_server.yml -e 'phantom_admin_password=${var.config.attack_range_password} phantom_community_username=${var.config.phantom_community_username} phantom_community_password=${var.config.phantom_community_password} phantom_server_private_ip=${var.config.phantom_server_private_ip}'"
  }

}
