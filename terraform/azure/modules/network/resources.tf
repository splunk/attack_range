
resource "azurerm_resource_group" "attackrange" {
  name = "ar-rg-${var.general.key_name}-${var.general.attack_range_name}"
  location = var.azure.location
}

resource "azurerm_virtual_network" "attackrange-network" {
  name = "ar-vnet-${var.general.key_name}-${var.general.attack_range_name}"
  address_space = ["10.0.0.0/16"]
  location = var.azure.location
  resource_group_name = azurerm_resource_group.attackrange.name
}

resource "azurerm_subnet" "attackrange-subnet" {
  name                 = "ar-subnet-${var.general.key_name}-${var.general.attack_range_name}"
  resource_group_name  = azurerm_resource_group.attackrange.name
  virtual_network_name = azurerm_virtual_network.attackrange-network.name
  address_prefixes       = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "attackrange-nsg" {
  name                = "ar-nsg-${var.general.key_name}-${var.general.attack_range_name}"
  location = var.azure.location
  resource_group_name  = azurerm_resource_group.attackrange.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Splunk_8000"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8000"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Splunk_8089"
    priority                   = 1003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8089"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  # RDP
  security_rule {
    name                       = "RDP"
    priority                   = 1004
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  # WinRM
  security_rule {
    name                       = "WinRM"
    priority                   = 1005
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5985-5986"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }


  # Allow all traffic from the private subnet
  security_rule {
    name                       = "PrivateSubnet"
    priority                   = 1007
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "10.0.1.0/24"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTP"
    priority                   = 1008
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTPS"
    priority                   = 1009
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Caldera"
    priority                   = 1010
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8888"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Prelude1"
    priority                   = 1011
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3391"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Prelude2"
    priority                   = 1012
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "2323"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Prelude3"
    priority                   = 1013
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "50051"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Guacamole"
    priority                   = 1014
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8080"
    source_address_prefixes    = [var.general.ip_whitelist]
    destination_address_prefix = "*"
  }

}

resource "azurerm_subnet_network_security_group_association" "attackrange-nsga" {
  subnet_id                 = azurerm_subnet.attackrange-subnet.id
  network_security_group_id = azurerm_network_security_group.attackrange-nsg.id
}