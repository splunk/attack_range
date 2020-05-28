
variable "private_key_path" {
  description = <<DESCRIPTION
Path to the SSH private key to be used for authentication.
Ensure this keypair is added to your local SSH agent so provisioners can
connect.

Example: ~/.ssh/terraform.key
Defaults to: ~/.ssh/id_rsa
DESCRIPTION
  default = "~/.ssh/id_rsa"
}


variable "key_name" {
  description = "Desired name of AWS key pair"
}

variable "vpc_security_group_ids" { }

variable "vpc_subnet_id" { }

variable "splunk_server_private_ip" { }

variable "use_packer_amis" { }
variable "splunk_packer_ami" { }

variable "phantom_app" { }
variable "phantom_server" { }
variable "phantom_server_private_ip" { }
variable "phantom_admin_password" { }

variable "phantom_server_instance" { }
variable "phantom_server_instance_packer" { }

#ansible variables
# ---------------------- #
# Splunk server
variable "splunk_admin_password" { }

variable "splunk_url" { }

variable "splunk_binary" { }

variable "s3_bucket_url" { }

variable "splunk_escu_app" { }

variable "splunk_asx_app" { }

variable "splunk_windows_ta" { }

variable "splunk_cim_app" { }

variable "splunk_sysmon_ta" { }

variable "caldera_password" { }

variable "splunk_python_app" { }

variable "splunk_mltk_app" { }

variable "splunk_bots_dataset" { }

variable "install_es" { }
variable "install_mltk" { }
variable "splunk_es_app" { }

variable "splunk_security_essentials_app" { }

variable "punchard_custom_visualization" { }
variable "status_indicator_custom_visualization" { }
variable "splunk_attack_range_dashboard" { }
variable "timeline_custom_visualization" { }
variable "install_mission_control" { }
variable "mission_control_app" { }
variable "install_dsp" { }
variable "dsp_client_cert_path" { }
variable "dsp_node" { }

variable "splunk_stream_app" { }
