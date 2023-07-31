module "networkModule" {
  source = "./modules/network"
  general = var.general
  aws = var.aws
}

module "splunk-server" {
  source = "./modules/splunk-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id = module.networkModule.ec2_subnet_id
  aws = var.aws
  splunk_server = var.splunk_server
  phantom_server = var.phantom_server
  general = var.general
  simulation = var.simulation
  windows_servers = var.windows_servers
  linux_servers = var.linux_servers
  kali_server = var.kali_server
  zeek_server = var.zeek_server
}

module "phantom-server" {
  source = "./modules/phantom-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id = module.networkModule.ec2_subnet_id
  phantom_server = var.phantom_server
  general = var.general
  aws = var.aws
  splunk_server = var.splunk_server
}

module "windows-server" {
  source = "./modules/windows"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id = module.networkModule.ec2_subnet_id
  general = var.general
  aws = var.aws
  windows_servers = var.windows_servers
  simulation = var.simulation
  zeek_server = var.zeek_server
  splunk_server = var.splunk_server
  
}

module "linux-server" {
  source = "./modules/linux-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id = module.networkModule.ec2_subnet_id
  general = var.general
  aws = var.aws
  linux_servers = var.linux_servers
  simulation = var.simulation
  zeek_server = var.zeek_server
  splunk_server = var.splunk_server
}

module "kali-server" {
  source = "./modules/kali-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id = module.networkModule.ec2_subnet_id
  general = var.general
  kali_server = var.kali_server
  aws = var.aws
}

module "nginx-server" {
  source = "./modules/nginx-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id = module.networkModule.ec2_subnet_id
  general = var.general
  nginx_server = var.nginx_server
  aws = var.aws
  splunk_server = var.splunk_server
}

module "zeek-server" {
  source = "./modules/zeek-server"
	vpc_security_group_ids = module.networkModule.sg_vpc_id
	ec2_subnet_id = module.networkModule.ec2_subnet_id
  general = var.general
  aws = var.aws
  zeek_server = var.zeek_server
  windows_servers = var.windows_servers
  windows_server_instances = module.windows-server.windows_servers
  linux_servers = var.linux_servers
  linux_server_instances = module.linux-server.linux_servers
  splunk_server = var.splunk_server
}