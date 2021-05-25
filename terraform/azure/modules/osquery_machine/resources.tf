resource "azurerm_public_ip" "linux-osquery-publicip" {
  count               = var.config.osquery_machine == "1" ? 1 : 0  
  name                = "ar-linux-osquery-ip-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "linux-osquery-nic" {
  count               = var.config.osquery_machine == "1" ? 1 : 0  
  name                = "ar-linux-osquery-nic-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-linux-osquery-nic-conf--${var.config.range_name}-${var.config.key_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.config.osquery_linux_private_ip
    public_ip_address_id          = azurerm_public_ip.linux-osquery-publicip[count.index].id
  }
}

resource "azurerm_virtual_machine" "linux-osquery" {
  count                 = var.config.osquery_machine == "1" ? 1 : 0  
  name = "ar-linux-osquery-${var.config.range_name}-${var.config.key_name}"
  location = var.config.region
  resource_group_name   = var.rg_name
  network_interface_ids = [azurerm_network_interface.linux-osquery-nic[count.index].id]
  vm_size               = var.config.instance_type_vms
  delete_os_disk_on_termination = true

  storage_os_disk {
    name              = "disk-linux-osquery-${var.config.range_name}-${var.config.key_name}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  storage_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }

  os_profile {
    computer_name  = "azure-${var.config.range_name}-linux-osquery"
    admin_username = "ubuntu"
    admin_password = var.config.attack_range_password
  }

  os_profile_linux_config {
    disable_password_authentication = true
    ssh_keys {
      path     = "/home/ubuntu/.ssh/authorized_keys"
      key_data = file(var.config.public_key_path)
    }
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = azurerm_public_ip.linux-osquery-publicip[count.index].ip_address
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.config.private_key_path} -i '${azurerm_public_ip.linux-osquery-publicip[count.index].ip_address},' playbooks/osquery_machine.yml -e 'splunk_indexer_ip=${var.config.splunk_server_private_ip} splunk_uf_url=${var.config.splunk_uf_linux_deb_url} custom_osquery_conf=${var.config.osquery_custom_config_file}'"

  }

}
