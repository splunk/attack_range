# variable "private_key_path" {
#   description = <<DESCRIPTION
# Path to the SSH private key to be used for authentication.
# Ensure this keypair is added to your local SSH agent so provisioners can
# connect.
#
# Example: ~/.ssh/terraform.key
# Defaults to: ~/.ssh/id_rsa
# DESCRIPTION
#   default = "~/.ssh/id_rsa"
# }
#
# variable "win_username" {
# 	description = "Windows Host default username to use"
# 	type = string
# }
#
# variable "win_password" {
# 	description = "Windows Host default password to use"
# 	type = string
# }
#
# variable "key_name" {
#   description = "Desired name of AWS key pair"
# }
#
#
# variable "ip_whitelist" {
#   description = "A list of CIDRs that will be allowed to access the EC2 instances"
#   type        = list(string)
# }
#
#
# #environment variables
# variable "phantom_server" {
#   default = "1"
# }
#
# variable "windows_domain_controller" {
#   default = "1"
# }
#
# variable "windows_server" {
#   default = "0"
# }
#
# variable "windows_client" {
#   default = "0"
# }
#
# variable "kali_machine" {
#   default = "0"
# }
#
# variable "splunk_server_private_ip" { }
# variable "phantom_server_private_ip" { }
# variable "windows_domain_controller_private_ip" { }
# variable "windows_domain_controller_os" { }
# variable "windows_server_os" { }
# variable "windows_server_private_ip" { }
# variable "windows_server_join_domain" { }
# variable "kali_machine_private_ip" { }
#
# variable "use_packer_amis" { }
# variable "splunk_packer_ami" { }
# variable "windows_domain_controller_packer_ami" { }
# variable "windows_server_packer_ami" { }
#
# variable "windows_client_private_ip" { }
# variable "windows_client_join_domain" { }
# variable "windows_client_os" { }
# variable "windows_client_packer_ami" { }
#
# variable "phantom_packer_ami" { }
#
# variable "kali_machine_packer_ami" { }
#
# #ansible variables
# # ---------------------- #
# # general
# variable "region" { }
#
# variable "caldera_password" { }
#
# # Splunk server
# variable "splunk_admin_password" { }
# variable "splunk_url" { }
# variable "splunk_binary" { }
# variable "s3_bucket_url" { }
# variable "splunk_escu_app" { }
# variable "splunk_asx_app" { }
# variable "splunk_windows_ta" { }
# variable "splunk_cim_app" { }
# variable "splunk_sysmon_ta" { }
# variable "splunk_python_app" { }
# variable "splunk_mltk_app" { }
# variable "splunk_stream_app" { }
# variable "install_es" { }
# variable "install_mltk" { }
# variable "splunk_es_app" { }
# variable "phantom_app" { }
# variable "splunk_bots_dataset" { }
# variable "splunk_security_essentials_app" { }
# variable "punchard_custom_visualization" { }
# variable "status_indicator_custom_visualization" { }
# variable "splunk_attack_range_dashboard" { }
# variable "timeline_custom_visualization" { }
# variable "install_mission_control" { }
# variable "mission_control_app" { }
# variable "install_dsp" { }
# variable "dsp_client_cert_path" { }
# variable "dsp_node" { }
#
# variable "capture_attack_data" { }
#
#
# # Phantom server
# variable "phantom_admin_password" { }
# variable "phantom_community_username" { }
# variable "phantom_community_password" { }
#
# # Windows server
# variable "splunk_uf_win_url" { }
# variable "nxlog_url" { }
# variable "win_sysmon_url" { }
# variable "win_sysmon_template" { }
#
# # Demo mode
# variable "run_demo" { }
# variable "demo_scenario" { }
#
# # cloud
# variable "cloud_attack_range" { }
#
# variable "splunk_aws_app" { }
#
# variable "cloud_s3_bucket" { }
# variable "cloud_s3_bucket_key" { }
#
# variable "cloudtrail" { }
# variable "cloudtrail_bucket" { }
#
# # kubernetes
# variable "kubernetes" { }


variable "config" { }
