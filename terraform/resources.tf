
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
	vpc_security_group_ids = "${module.networkModule.vpc_security_group_ids}"
	vpc_subnet1_id         = "${module.networkModule.vpc_subnet1_id}"
}
