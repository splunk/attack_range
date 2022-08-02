resource "azurerm_public_ip" "linux-publicip" {
  count = length(var.linux_servers)
  name                = "ar-linux-ip-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location            = var.azure.location
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "linux-nic" {
  count = length(var.linux_servers)
  name                = "ar-linux-nic-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location            = var.azure.location
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-linux-nic-conf-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.0.1.${21 + count.index}"
    public_ip_address_id          = azurerm_public_ip.linux-publicip[count.index].id
  }
}

data "azurerm_image" "search" {
  count = length(var.linux_servers)
  name                = var.linux_servers[count.index].image
  resource_group_name = "packer_${replace(var.azure.location, " ", "_")}"
}

resource "azurerm_virtual_machine" "linux" {
  count = length(var.linux_servers)
  name = "ar-linux-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  location = var.azure.location
  resource_group_name  = var.rg_name
  network_interface_ids = [azurerm_network_interface.linux-nic[count.index].id]
  vm_size               = "Standard_A4_v2"
  delete_os_disk_on_termination = true

  storage_os_disk {
    name              = "disk-linux-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  storage_image_reference {
    id = data.azurerm_image.search[count.index].id
  }

  os_profile {
    computer_name  = var.linux_servers[count.index].hostname
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
      host        = azurerm_public_ip.linux-publicip[count.index].ip_address
      private_key = file(var.azure.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.azure.private_key_path} -i '${azurerm_public_ip.linux-publicip[count.index].ip_address},' linux_server_post.yml -e 'ansible_python_interpreter=/usr/bin/python3 ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.linux_servers[count.index] : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.simulation : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])}'"
  }

}