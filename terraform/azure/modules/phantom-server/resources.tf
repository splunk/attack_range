resource "azurerm_public_ip" "phantom-publicip" {
  count       = var.phantom_server.phantom_server == "1" ? 1 : 0
  name                = "ar-phantom-ip-${var.general.key_name}-${var.general.attack_range_name}"
  location            = var.azure.location
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "phantom-nic" {
  count       = var.phantom_server.phantom_server == "1" ? 1 : 0
  name                = "ar-phantom-nic-${var.general.key_name}-${var.general.attack_range_name}"
  location            = var.azure.location
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-phantom-nic-conf-${var.general.key_name}-${var.general.attack_range_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.0.1.13"
    public_ip_address_id          = azurerm_public_ip.phantom-publicip[count.index].id
  }
}

data "azurerm_image" "phantom" {
  count               = (var.phantom_server.phantom_server == "1") && (var.general.use_prebuilt_images_with_packer == "1") ? 1 : 0
  name                = var.phantom_server.phantom_image
  resource_group_name = "packer_${replace(var.azure.location, " ", "_")}"
}

resource "azurerm_virtual_machine" "phantom" {
  count       = var.phantom_server.phantom_server == "1" ? 1 : 0
  name = "ar-phantom-${var.general.key_name}-${var.general.attack_range_name}"
  location = var.azure.location
  resource_group_name  = var.rg_name
  network_interface_ids = [azurerm_network_interface.phantom-nic[count.index].id]
  vm_size               = "Standard_B8als_v2"

  delete_os_disk_on_termination = true

  storage_os_disk {
    name              = "disk-phantom-${var.general.key_name}-${var.general.attack_range_name}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  storage_image_reference {
    id = var.general.use_prebuilt_images_with_packer == "1" ? data.azurerm_image.phantom[0].id : null
    publisher = var.general.use_prebuilt_images_with_packer == "0" ? "almalinux" : null 
    offer     = var.general.use_prebuilt_images_with_packer == "0" ? "almalinux-x86_64" : null
    sku       = var.general.use_prebuilt_images_with_packer == "0" ? "8-gen1" : null
    version   = var.general.use_prebuilt_images_with_packer == "0" ? "latest" : null
  }

  os_profile {
    computer_name  = "azure-phantom"
    admin_username = "almalinux"
    admin_password = var.general.attack_range_password
  }

  os_profile_linux_config {
    disable_password_authentication = true
    ssh_keys {
      path     = "/home/almalinux/.ssh/authorized_keys"
      key_data = file(var.azure.public_key_path)
    }
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "almalinux"
      host        = azurerm_public_ip.phantom-publicip[count.index].ip_address
      private_key = file(var.azure.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../packer/ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u almalinux --private-key ${var.azure.private_key_path} -i '${azurerm_public_ip.phantom-publicip[0].ip_address},' phantom_server.yml -e '${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.phantom_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])}'"
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u almalinux --private-key ${var.azure.private_key_path} -i '${azurerm_public_ip.phantom-publicip[0].ip_address},' phantom_server.yml -e '${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.phantom_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.azure : "${key}=\"${value}\""])}'"
  }

}
