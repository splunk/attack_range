
# Ressource group
output "rg_name" {
  value = azurerm_resource_group.attackrange.name
}

# Subnet id
output "subnet_id" {
  value = azurerm_subnet.attackrange-subnet.id
}
