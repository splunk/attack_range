
variable "cloud_attack_range" { }
variable "vpc_id" { }
variable "subnet_db1" { }
variable "availability_zone_db1" { }
variable "subnet_db2" { }
variable "availability_zone_db2" { }
variable "key_name" { }
variable "db_user" { }
variable "db_password" { }
variable "ip_whitelist" {
  type        = list(string)
}
