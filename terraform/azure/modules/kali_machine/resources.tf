
resource "azurerm_public_ip" "kali-publicip" {
  count       = var.config.kali_machine == "1" ? 1 : 0
  name                = "ar-kali-ip-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "kali-nic" {
  count       = var.config.kali_machine == "1" ? 1 : 0
  name                = "ar-kali-nic-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-kali-nic-conf--${var.config.range_name}-${var.config.key_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.config.kali_machine_private_ip
    public_ip_address_id          = azurerm_public_ip.kali-publicip[count.index].id
  }
}

resource "azurerm_virtual_machine" "kali" {
  count       = var.config.kali_machine == "1" ? 1 : 0
  name = "ar-kali-${var.config.range_name}-${var.config.key_name}"
  location = var.config.region
  resource_group_name  = var.rg_name
  network_interface_ids = [azurerm_network_interface.kali-nic[count.index].id]
  vm_size               = var.config.instance_type_vms

  delete_os_disk_on_termination = true

  storage_os_disk {
    name              = "disk-kali-${var.config.range_name}-${var.config.key_name}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  plan {
    publisher = "kali-linux"
    product   = "kali-linux"
    name      = "kali"
  }

  storage_image_reference {
    publisher = "kali-linux"
    offer     = "kali-linux"
    sku       = "kali"
    version   = "latest"
  }

  os_profile {
    computer_name  = "azure-${var.config.range_name}-kali"
    admin_username = "kali"
    admin_password = var.config.attack_range_password
  }

  os_profile_linux_config {
    disable_password_authentication = true
    ssh_keys {
      path     = "/home/kali/.ssh/authorized_keys"
      key_data = file(var.config.public_key_path)
    }
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "kali"
      host        = azurerm_public_ip.kali-publicip[count.index].ip_address
      private_key = file(var.config.private_key_path)
    }
  }
}
