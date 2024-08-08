variable "general" {
  type = map(string)

  default = {
    attack_range_password = "Pl3ase-k1Ll-me:p"
    key_name              = "attack-range-key-pair"
    attack_range_name     = "ar"
    ip_whitelist          = "0.0.0.0/0"
    network_prefix        = "10.211.16"
    network_cidr          = "10.211.16.96/28"
  }
}

variable "aws" {
  type = map(string)

  default = {
    region           = "us-east-1"
    private_key_path = "~/.ssh/id_rsa"
  }
}

variable "splunk_server" {
  type = map(string)

  default = {
    install_es       = "0"
    splunk_es_app    = "splunk-enterprise-security_701.spl"
    splunk_server_ip = "10.211.16.100"
  }
}

variable "phantom_server" {
  type = map(string)

  default = {
    phantom_server             = "0"
    phantom_community_username = "user"
    phantom_community_password = "password"
    phantom_repo_url           = "https://repo.phantom.us/phantom/5.2/base/7/x86_64/phantom_repo-5.2.1.78411-1.x86_64.rpm"
    phantom_version            = "5.2.1.78411-1"
    phantom_server_ip          = "10.211.16.101"
  }
}

variable "windows_servers" {
  type = list(any)

  default = [
    {
      hostname               = "ar-win"
      image                  = "windows-2019-2-0-0"
      win_sysmon_config      = "SwiftOnSecurity.xml"
      create_domain          = "0"
      join_domain            = "0"
      install_red_team_tools = "0"
      start_ip               = "10.211.16.105"
    }
  ]
}

variable "linux_servers" {
  type = list(any)

  default = [
    {
      hostname      = "ar-linux"
      image         = "ubuntu-18-04-v2-0-0"
      sysmon_config = "configs/SwiftOnSecurity.xml"
      start_ip      = "10.211.16.107"
    }
  ]
}

variable "simulation" {}

variable "kali_server" {
  type = map(string)

  default = {
    kali_server    = "0"
    kali_server_ip = "10.211.16.103"
  }
}

variable "nginx_server" {
  type = map(string)

  default = {
    nginx_server      = "0"
    image             = "nginx-web-proxy-v3-0-0"
    nginx_server_ip   = "10.211.16.104"
    proxy_server_ip   = "10.211.16.100"
    proxy_server_port = "8000"
  }
}

variable "zeek_server" {
  type = map(string)

  default = {
    zeek_server    = "0"
    zeek_server_ip = "10.211.16.102"
  }
}

variable "vpc_id" {}

variable "ec2_subnet_id" {}
