provider "aws" {
  profile    =  var.aws_profile
  region     =  var.aws_region
}

module "networkModule" {
  source			  = "./modules/network"
 	vpc_cidr		  = "${var.vpc_cidr}"
	subnets		    = "${var.subnets}"
  aws_profile   = "${var.aws_profile}"
	aws_region		= "${var.aws_region}"
	ip_whitelist  = "${var.ip_whitelist}"
}

module "splunk-server" {
  source			           = "./modules/splunk-server"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  splunk_ami             = "${var.splunk_ami}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet1_id         = "${module.networkModule.vpc_subnet1_id}"
  splunk_admin_password  = "${var.splunk_admin_password}"
  splunk_url             = "${var.splunk_url}"
  splunk_binary          = "${var.splunk_binary}"
  s3_bucket_url          = "${var.s3_bucket_url}"
  splunk_escu_app        = "${var.splunk_escu_app}"
  splunk_asx_app         = "${var.splunk_asx_app}"
  splunk_windows_ta      = "${var.splunk_windows_ta}"
  splunk_cim_app         = "${var.splunk_cim_app}"
  splunk_sysmon_ta       = "${var.splunk_sysmon_ta}"

}

module "windows-2016-dc" {
  source			           = "./modules/windows-2016-dc"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  win_username		       = "${var.win_username}"
  win_password		       = "${var.win_password}"
  windows_2016_dc_ami    = "${var.windows_2016_dc_ami}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
  windows_dc_server_private_ip = "${var.windows_dc_server_private_ip}"
  windows_2016_dc		      = "${var.windows_2016_dc}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet0_id         = "${module.networkModule.vpc_subnet0_id}"
  splunk_uf_win_url      = "${var.splunk_uf_win_url}"
  win_sysmon_url         = "${var.win_sysmon_url}"
  win_sysmon_template    = "${var.win_sysmon_template}"
  splunk_admin_password  = "${var.splunk_admin_password}"
}


module "windows-2016-dc-client" {
  source			           = "./modules/windows-2016-dc-client"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  win_username		       = "${var.win_username}"
  win_password		       = "${var.win_password}"
  windows_2016_dc_ami    = "${var.windows_2016_dc_ami}"
  splunk_server_private_ip = "${var.splunk_server_private_ip}"
  windows_2016_dc_client = "${var.windows_2016_dc_client}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet0_id         = "${module.networkModule.vpc_subnet0_id}"
  windows_2016_dc_instance = "${module.windows-2016-dc.windows_2016_dc_instance}"
  splunk_uf_win_url      = "${var.splunk_uf_win_url}"
  win_sysmon_url         = "${var.win_sysmon_url}"
  win_sysmon_template    = "${var.win_sysmon_template}"
  splunk_admin_password  = "${var.splunk_admin_password}"
}

module "kali-machine" {
  source			           = "./modules/kali-machine"
 	private_key_path       = "${var.private_key_path}"
	key_name		           = "${var.key_name}"
  kali_ami               = "${var.kali_ami}"
  kali-machine           = "${var.kali-machine}"
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet0_id         = "${module.networkModule.vpc_subnet0_id}"
}
