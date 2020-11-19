provider "aws" {
  region     =  var.config.region
}

module "networkModule" {
  source			  = "./modules/network"
  config                = var.config
}

module "splunk-server" {
  source			           = "./modules/splunk-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id         = module.networkModule.ec2_subnet_id
  phantom_server_instance = module.phantom-server.phantom_server_instance
  config                = var.config
}

module "phantom-server" {
  source                     = "./modules/phantom-server"
  vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id          = module.networkModule.ec2_subnet_id
  config                 = var.config
}

module "windows-domain-controller" {
  source			           = "./modules/windows-domain-controller"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id          = module.networkModule.ec2_subnet_id
  config                 = var.config
}

module "windows-server" {
  source			           = "./modules/windows-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id          = module.networkModule.ec2_subnet_id
  windows_domain_controller_instance = module.windows-domain-controller.windows_domain_controller_instance
  config                 = var.config
}

module "windows-client" {
  source			           = "./modules/windows-client"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id          = module.networkModule.ec2_subnet_id
  windows_domain_controller_instance = module.windows-domain-controller.windows_domain_controller_instance
  config                 = var.config
}

module "kali_machine" {
  source			           = "./modules/kali_machine"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id          = module.networkModule.ec2_subnet_id
  config                 = var.config
}

module "zeek_sensor" {
  source			           = "./modules/zeek_sensor"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id          = module.networkModule.ec2_subnet_id
  windows_domain_controller_instance = module.windows-domain-controller.windows_domain_controller_instance
  windows_server_instance = module.windows-server.windows_server_instance
  windows_client_instance = module.windows-client.windows_client_instance
  config                 = var.config
}
