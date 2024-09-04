module "networkModule" {
  source  = "./modules/network"
  general = var.general
  aws     = var.aws
}

module "splunk-server" {
  source                 = "./modules/splunk-server"
  vpc_security_group_ids = module.networkModule.sg_vpc_id
  ec2_subnet_id          = module.networkModule.ec2_subnet_id
  aws                    = var.aws
  splunk_server          = var.splunk_server
  phantom_server         = var.phantom_server
  general                = var.general
  simulation             = var.simulation
  windows_servers        = var.windows_servers
  linux_servers          = var.linux_servers
  kali_server            = var.kali_server
  zeek_server            = var.zeek_server
  snort_server           = var.snort_server
  role_arn               = aws_iam_role.this.arn
  instance_profile_name  = aws_iam_instance_profile.this.name
}

module "phantom-server" {
  source                 = "./modules/phantom-server"
  vpc_security_group_ids = module.networkModule.sg_vpc_id
  ec2_subnet_id          = module.networkModule.ec2_subnet_id
  phantom_server         = var.phantom_server
  general                = var.general
  aws                    = var.aws
  splunk_server          = var.splunk_server
  instance_profile_name  = aws_iam_instance_profile.this.name
}

module "windows-server" {
  source                 = "./modules/windows"
  vpc_security_group_ids = module.networkModule.sg_vpc_id
  ec2_subnet_id          = module.networkModule.ec2_subnet_id
  general                = var.general
  aws                    = var.aws
  windows_servers        = var.windows_servers
  simulation             = var.simulation
  zeek_server            = var.zeek_server
  snort_server           = var.snort_server
  splunk_server          = var.splunk_server
  instance_profile_name  = aws_iam_instance_profile.this.name

}

module "linux-server" {
  source                 = "./modules/linux-server"
  vpc_security_group_ids = module.networkModule.sg_vpc_id
  ec2_subnet_id          = module.networkModule.ec2_subnet_id
  general                = var.general
  aws                    = var.aws
  zeek_server            = var.zeek_server
  snort_server           = var.snort_server
  linux_servers          = var.linux_servers
  simulation             = var.simulation
  splunk_server          = var.splunk_server
  instance_profile_name  = aws_iam_instance_profile.this.name
}

module "kali-server" {
  source                 = "./modules/kali-server"
  vpc_security_group_ids = module.networkModule.sg_vpc_id
  ec2_subnet_id          = module.networkModule.ec2_subnet_id
  general                = var.general
  kali_server            = var.kali_server
  aws                    = var.aws
}

module "nginx-server" {
  source                 = "./modules/nginx-server"
  vpc_security_group_ids = module.networkModule.sg_vpc_id
  ec2_subnet_id          = module.networkModule.ec2_subnet_id
  general                = var.general
  nginx_server           = var.nginx_server
  aws                    = var.aws
  splunk_server          = var.splunk_server
}

module "zeek-server" {
  source                   = "./modules/zeek-server"
  vpc_security_group_ids   = module.networkModule.sg_vpc_id
  ec2_subnet_id            = module.networkModule.ec2_subnet_id
  general                  = var.general
  aws                      = var.aws
  zeek_server              = var.zeek_server
  windows_servers          = var.windows_servers
  windows_server_instances = module.windows-server.windows_servers
  linux_servers            = var.linux_servers
  linux_server_instances   = module.linux-server.linux_servers
  splunk_server            = var.splunk_server
}

module "snort-server" {
  source                   = "./modules/snort-server"
  vpc_security_group_ids   = module.networkModule.sg_vpc_id
  ec2_subnet_id            = module.networkModule.ec2_subnet_id
  general                  = var.general
  aws                      = var.aws
  snort_server             = var.snort_server
  windows_servers          = var.windows_servers
  windows_server_instances = module.windows-server.windows_servers
  linux_servers            = var.linux_servers
  linux_server_instances   = module.linux-server.linux_servers
  splunk_server            = var.splunk_server
}

module "nlb_security_group" {
  source  = "./modules/nlb_security_group"
  general = var.general
  aws     = var.aws
}

module "elb_security_group" {
  source  = "./modules/elb_security_group"
  general = var.general
  aws     = var.aws
}

module "bastion_host" {
  source                = "./modules/bastion_host"
  ec2_subnet_id         = module.networkModule.ec2_subnet_id
  general               = var.general
  aws                   = var.aws
  instance_profile_name = aws_iam_instance_profile.this.name
}

module "edge_processor" {
  source                         = "./modules/edge_processor"
  general                        = var.general
  aws                            = var.aws
  edge_processor                 = var.edge_processor
  splunk_server                  = var.splunk_server
  nlb_security_group_id          = module.nlb_security_group.id
  bastion_host_security_group_id = module.bastion_host.security_group_id
  instance_profile_name          = aws_iam_instance_profile.this.name
}

module "route53" {
  source   = "./modules/route53"
  dns_zone = var.general.dns_zone
  vpc_id   = var.aws.vpc_id
}

module "apache_httpd" {
  source                         = "./modules/apache/httpd"
  general                        = var.general
  aws                            = var.aws
  httpd_server                   = var.httpd_server
  splunk_server                  = var.splunk_server
  elb_security_group_id          = module.elb_security_group.id
  bastion_host_security_group_id = module.bastion_host.security_group_id
  instance_profile_name          = aws_iam_instance_profile.this.name
}

module "network_load_balancer" {
  source                     = "./modules/nlb"
  ec2_subnet_id              = module.networkModule.ec2_subnet_id
  general                    = var.general
  aws                        = var.aws
  edge_processor             = var.edge_processor
  nlb_security_group_id      = module.nlb_security_group.id
  edge-processor_instance_id = module.edge_processor.instance_id
}

module "application_load_balancer" {
  source                   = "./modules/elb"
  ec2_subnet_id            = module.networkModule.ec2_subnet_id
  general                  = var.general
  aws                      = var.aws
  httpd_server             = var.httpd_server
  elb_security_group_id    = module.elb_security_group.id
  apache-httpd_instance_id = module.apache_httpd.instance_id
}

module "waf" {
  source              = "./modules/waf-regional"
  waf_prefix          = "${var.general.name_prefix}-${var.general.attack_range_name}"
  enable_logging      = true
  log_destination_arn = module.firehose.kinesis_firehose_arn
  resource_arn        = [module.application_load_balancer.arn]
  custom_csrf_token = [
    {
      field    = "x-twilio-signature"
      size     = 28
      operator = "GT"
    }
  ]
}

resource "random_pet" "this" {
  length = 2
}

resource "aws_s3_bucket" "s3" {
  bucket        = "${var.general.name_prefix}-${var.general.key_name}-${var.general.attack_range_name}-${random_pet.this.id}"
  force_destroy = true
}

resource "aws_kms_key" "this" {
  description             = "${var.general.name_prefix}-${var.general.attack_range_name}-kms-key"
  deletion_window_in_days = 7
}

module "firehose" {
  source                = "./modules/firehose"
  general               = var.general
  waf                   = var.waf
  destination           = "splunk"
  input_source          = "waf"
  s3_backup_bucket_arn  = aws_s3_bucket.s3.arn
  s3_backup_kms_key_arn = aws_kms_key.this.arn
}
