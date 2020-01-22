provider "aws" {
  region     =  "${var.region}"
}

module "networkModule" {
  source			  = "./modules/network"
	ip_whitelist  = "${var.ip_whitelist}"
  availability_zone = "${var.availability_zone}"
  subnet_cidr   = "${var.subnet_cidr}"
}

module "splunk-server" {
  source			           = "./modules/splunk-server"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet_id         = "${module.networkModule.vpc_subnet_id}"
  splunk_admin_password  = "${var.splunk_admin_password}"
  splunk_url             = "${var.splunk_url}"
  splunk_binary          = "${var.splunk_binary}"
  s3_bucket_url          = "${var.s3_bucket_url}"
  splunk_escu_app        = "${var.splunk_escu_app}"
  splunk_asx_app         = "${var.splunk_asx_app}"
  splunk_windows_ta      = "${var.splunk_windows_ta}"
  splunk_cim_app         = "${var.splunk_cim_app}"
  splunk_sysmon_ta       = "${var.splunk_sysmon_ta}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
  use_packer_amis        = "${var.use_packer_amis}"
  splunk_packer_ami      = "${var.splunk_packer_ami}"
}

module "windows-domain-controller" {
  source			           = "./modules/windows-domain-controller"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  win_username		       = "${var.win_username}"
  win_password		       = "${var.win_password}"
  windows_domain_controller		      = "${var.windows_domain_controller}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet_id          = "${module.networkModule.vpc_subnet_id}"
  splunk_uf_win_url      = "${var.splunk_uf_win_url}"
  win_sysmon_url         = "${var.win_sysmon_url}"
  win_sysmon_template    = "${var.win_sysmon_template}"
  splunk_admin_password  = "${var.splunk_admin_password}"
  availability_zone      = "${var.availability_zone}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
  windows_domain_controller_private_ip = "${var.windows_domain_controller_private_ip}"
  windows_domain_controller_os = "${var.windows_domain_controller_os}"
  use_packer_amis        = "${var.use_packer_amis}"
  windows_domain_controller_packer_ami = "${var.windows_domain_controller_packer_ami}"
}


module "windows-server" {
  source			           = "./modules/windows-server"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  win_username		       = "${var.win_username}"
  win_password		       = "${var.win_password}"
  windows_server = "${var.windows_server}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet_id          = "${module.networkModule.vpc_subnet_id}"
  windows_domain_controller_instance = "${module.windows-domain-controller.windows_domain_controller_instance}"
  splunk_uf_win_url      = "${var.splunk_uf_win_url}"
  win_sysmon_url         = "${var.win_sysmon_url}"
  win_sysmon_template    = "${var.win_sysmon_template}"
  splunk_admin_password  = "${var.splunk_admin_password}"
  availability_zone      = "${var.availability_zone}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
  windows_server_private_ip = "${var.windows_server_private_ip}"
  windows_domain_controller_private_ip = "${var.windows_domain_controller_private_ip}"
  windows_server_os      = "${var.windows_server_os}"
  windows_server_join_domain = "${var.windows_server_join_domain}"
}

module "kali_machine" {
  source			           = "./modules/kali_machine"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  kali_machine           = "${var.kali_machine}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet_id          = "${module.networkModule.vpc_subnet_id}"
  kali_machine_private_ip = "${var.kali_machine_private_ip}"
}
