
resource "azurerm_public_ip" "splunk-publicip" {
  count               = var.splunk_server.byo_splunk == "0" ? 1 : 0
  name                = "ar-splunk-ip-${var.general.key_name}-${var.general.attack_range_name}"
  location            = var.azure.location
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "splunk-nic" {
  count               = var.splunk_server.byo_splunk == "0" ? 1 : 0
  name                = "ar-splunk-nic-${var.general.key_name}-${var.general.attack_range_name}"
  location            = var.azure.location
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-splunk-nic-conf-${var.general.key_name}-${var.general.attack_range_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.0.1.12"
    public_ip_address_id          = azurerm_public_ip.splunk-publicip[0].id
  }
}

resource "azurerm_virtual_machine" "splunk" {
  count = var.splunk_server.byo_splunk == "0" ? 1 : 0
  name = "ar-splunk-${var.general.key_name}-${var.general.attack_range_name}"
  location = var.azure.location
  resource_group_name  = var.rg_name
  network_interface_ids = [azurerm_network_interface.splunk-nic[0].id]
  vm_size               = "Standard_D4_v4"
#  depends_on             = [var.phantom_server_instance]
  delete_os_disk_on_termination = true

  storage_os_disk {
    name              = "disk-splunk-${var.general.key_name}-${var.general.attack_range_name}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  storage_image_reference {
    publisher = "canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  os_profile {
    computer_name  = "azure-splunk"
    admin_username = "ubuntu"
    admin_password = var.general.attack_range_password
  }

  os_profile_linux_config {
    disable_password_authentication = true
    ssh_keys {
      path     = "/home/ubuntu/.ssh/authorized_keys"
      key_data = file(var.azure.public_key_path)
    }
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = azurerm_public_ip.splunk-publicip[0].ip_address
      private_key = file(var.azure.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      cat <<EOF > vars/splunk_vars.json
      {
        "ansible_python_interpreter": "/usr/bin/python3",
        "general": ${jsonencode(var.general)},
        "azure": ${jsonencode(var.azure)},
        "splunk_server": ${jsonencode(var.splunk_server)},
        "phantom_server": ${jsonencode(var.phantom_server)},
        "kali_server": ${jsonencode(var.kali_server)},
        "simulation": ${jsonencode(var.simulation)},
        "zeek_server": ${jsonencode(var.zeek_server)},
        "snort_server": ${jsonencode(var.snort_server)},
        "windows_servers": ${jsonencode(var.windows_servers)},
        "linux_servers": ${jsonencode(var.linux_servers)},
      }
      EOF
    EOT
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key '${var.azure.private_key_path}' -i '${azurerm_public_ip.splunk-publicip[0].ip_address},' splunk_server.yml -e "@vars/splunk_vars.json"
    EOT
  }

}