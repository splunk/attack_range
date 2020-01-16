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
}

module "windows-2016-dc" {
  source			           = "./modules/windows-2016-dc"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  win_username		       = "${var.win_username}"
  win_password		       = "${var.win_password}"
  windows_2016_dc		      = "${var.windows_2016_dc}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet_id          = "${module.networkModule.vpc_subnet_id}"
  splunk_uf_win_url      = "${var.splunk_uf_win_url}"
  win_sysmon_url         = "${var.win_sysmon_url}"
  win_sysmon_template    = "${var.win_sysmon_template}"
  splunk_admin_password  = "${var.splunk_admin_password}"
  availability_zone      = "${var.availability_zone}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
  windows_2016_dc_private_ip = "${var.windows_2016_dc_private_ip}"
}


module "windows-2016-dc-client" {
  source			           = "./modules/windows-2016-dc-client"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  win_username		       = "${var.win_username}"
  win_password		       = "${var.win_password}"
  windows_2016_dc_client = "${var.windows_2016_dc_client}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet_id          = "${module.networkModule.vpc_subnet_id}"
  windows_2016_dc_instance = "${module.windows-2016-dc.windows_2016_dc_instance}"
  splunk_uf_win_url      = "${var.splunk_uf_win_url}"
  win_sysmon_url         = "${var.win_sysmon_url}"
  win_sysmon_template    = "${var.win_sysmon_template}"
  splunk_admin_password  = "${var.splunk_admin_password}"
  availability_zone      = "${var.availability_zone}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
  windows_2016_dc_client_private_ip = "${var.windows_2016_dc_client_private_ip}"
  windows_2016_dc_private_ip = "${var.windows_2016_dc_private_ip}"
}

module "kali-machine" {
  source			           = "./modules/kali-machine"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  kali-machine           = "${var.kali-machine}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet_id          = "${module.networkModule.vpc_subnet_id}"
  kali-machine_private_ip = "${var.kali-machine_private_ip}"
}
