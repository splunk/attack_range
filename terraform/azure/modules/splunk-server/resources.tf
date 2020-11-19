
resource "azurerm_public_ip" "splunk-publicip" {
  name                = "ar-splunk-ip-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name
  allocation_method   = "Static"
}

resource "azurerm_network_interface" "splunk-nic" {
  name                = "ar-splunk-nic-${var.config.range_name}-${var.config.key_name}"
  location            = var.config.region
  resource_group_name = var.rg_name

  ip_configuration {
    name                          = "ar-splunk-nic-conf--${var.config.range_name}-${var.config.key_name}"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.config.splunk_server_private_ip
    public_ip_address_id          = azurerm_public_ip.splunk-publicip.id
  }
}

resource "azurerm_virtual_machine" "splunk" {
  name = "ar-splunk-${var.config.range_name}-${var.config.key_name}"
  location = var.config.region
  resource_group_name  = var.rg_name
  network_interface_ids = [azurerm_network_interface.splunk-nic.id]
  vm_size               = var.config.instance_type_vms
  depends_on             = [var.phantom_server_instance]
  delete_os_disk_on_termination = true

  storage_os_disk {
    name              = "disk-splunk-${var.config.range_name}-${var.config.key_name}"
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
    computer_name  = "azure-${var.config.range_name}-splunk"
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
      host        = azurerm_public_ip.splunk-publicip.ip_address
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.config.private_key_path} -i '${azurerm_public_ip.splunk-publicip.ip_address},' playbooks/splunk_server.yml -e 'ansible_python_interpreter=/usr/bin/python3 splunk_admin_password=${var.config.attack_range_password} splunk_url=${var.config.splunk_url} splunk_binary=${var.config.splunk_binary} s3_bucket_url=${var.config.s3_bucket_url} splunk_escu_app=${var.config.splunk_escu_app} splunk_asx_app=${var.config.splunk_asx_app} splunk_windows_ta=${var.config.splunk_windows_ta} splunk_aws_ta=${var.config.splunk_aws_ta} splunk_cim_app=${var.config.splunk_cim_app} splunk_sysmon_ta=${var.config.splunk_sysmon_ta} splunk_python_app=${var.config.splunk_python_app} splunk_mltk_app=${var.config.splunk_mltk_app} caldera_password=${var.config.attack_range_password} install_es=${var.config.install_es} splunk_es_app=${var.config.splunk_es_app} phantom_app=${var.config.phantom_app} phantom_server=${var.config.phantom_server} phantom_server_private_ip=${var.config.phantom_server_private_ip} phantom_admin_password=${var.config.attack_range_password} splunk_security_essentials_app=${var.config.splunk_security_essentials_app} splunk_bots_dataset=${var.config.splunk_bots_dataset} punchard_custom_visualization=${var.config.punchard_custom_visualization} status_indicator_custom_visualization=${var.config.status_indicator_custom_visualization} splunk_attack_range_dashboard=${var.config.splunk_attack_range_dashboard} timeline_custom_visualization=${var.config.timeline_custom_visualization} splunk_stream_app=${var.config.splunk_stream_app} splunk_zeek_ta=${var.config.splunk_zeek_ta} splunk_server_private_ip=${var.config.splunk_server_private_ip}'"
  }

}
