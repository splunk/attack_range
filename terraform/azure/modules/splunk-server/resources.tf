
resource "azurerm_public_ip" "splunk-publicip" {
  name                = "ar-splunk-ip-${var.general.key_name}-${var.general.attack_range_name}"
  location            = var.azure.region
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "splunk-nic" {
  name                = "ar-splunk-nic-${var.general.key_name}-${var.general.attack_range_name}"
  location            = var.azure.region
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-splunk-nic-conf-${var.general.key_name}-${var.general.attack_range_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.0.1.12"
    public_ip_address_id          = azurerm_public_ip.splunk-publicip.id
  }
}

data "azurerm_image" "search" {
  name                = var.splunk_server.image
  resource_group_name = "packer_${replace(var.azure.region, " ", "_")}"
}

resource "azurerm_virtual_machine" "splunk" {
  name = "ar-splunk-${var.general.key_name}-${var.general.attack_range_name}"
  location = var.azure.region
  resource_group_name  = var.rg_name
  network_interface_ids = [azurerm_network_interface.splunk-nic.id]
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
    id = data.azurerm_image.search.id
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
      host        = azurerm_public_ip.splunk-publicip.ip_address
      private_key = file(var.azure.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.azure.private_key_path} -i '${azurerm_public_ip.splunk-publicip.ip_address},' splunk_server_post.yml -e 'ansible_python_interpreter=/usr/bin/python3 ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.azure : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.phantom_server : "${key}=\"${value}\""])}'"
  }

}