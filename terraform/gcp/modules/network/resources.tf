# Locals variables
# Creates a locals variables to obtain the first three octets of the private subnet.
# -----------------------------------------------------------------------------
# locals {
#   private_cidr_prefix = cidrsubnet(var.cidrs["cidr_blocks"][1], 0, 0) #Get private subnet
#   private_cidr_three_octets = join(".", slice(split(".", local.private_cidr_prefix), 0, 3))
# }

# -----------------------------------------------------------------------------
# VPC Module Configuration
# Creates a Google Compute Engine Virtual Private Cloud (VPC) with defined subnets.
# Utilizes the Terraform Google network module for custom public and private subnets.
# -----------------------------------------------------------------------------
module "vpc" {
  description            = "Google Compute Engine VPC network"
  source                 = "terraform-google-modules/network/google"
  version                = "9.3.0"
  project_id             = var.gcp.project_id
  network_name           = "vpc-${var.general.key_name}-${var.general.attack_range_name}"
  auto_create_subnetworks = false

  subnets = [
    {
      subnet_name   = "public-subnet"
      subnet_ip     = var.cidrs.cidr_blocks[0]  # Public subnet
      subnet_region = var.gcp.region
    }
  ]
}

# -----------------------------------------------------------------------------
# Static IP Address
# Allocates a static external IP for use with instances requiring a fixed IP.
# -----------------------------------------------------------------------------
resource "google_compute_address" "static_ip" {
  name   = "static-ip"
  region = var.gcp.region
}

resource "google_compute_firewall" "allow_icmp" { 

    description = "Allow ICMP from the IP whitelist" 
    name    = "allow-icmp" 
    network = module.vpc.network_name 

    allow { 
        protocol = "icmp" 
    } 

    source_ranges = split(",", var.general.ip_whitelist) 

} 

resource "google_compute_firewall" "allow_ar_ssh" { 

    description = "Allow SSH from the IP whitelist" 
    name    = "allow-ar-ssh" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["22"] 
    } 

    source_ranges = split(",", var.general.ip_whitelist) 

} 

resource "google_compute_firewall" "allow_telnet" { 

    description = "Allow Telnet from the IP whitelist" 
    name    = "allow-telnet" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["2323"] 
    } 

    source_ranges = split(",", var.general.ip_whitelist) 

} 

resource "google_compute_firewall" "allow_rdp" { 

    description = "Allow RDP services from the IP whitelist" 
    name    = "allow-rdp" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["3389", "3391"] 
    } 

    source_ranges = split(",", var.general.ip_whitelist) 
} 

resource "google_compute_firewall" "allow_winrm" { 

    description =  "Allow WinRM ports from the IP whitelistWinRM" 
    name    = "allow-winrm" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["5985", "5986"] 
    } 

    source_ranges = split(",", var.general.ip_whitelist) 

}   

resource "google_compute_firewall" "allow_custom_tcp_port" { 

    description =  "Allow custom TCP ports from the IP whitelistWinRM" 
    name    = "allow-custom-tcp-port" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["7999"] 
    } 

    source_ranges = split(",", var.general.ip_whitelist) 
} 

resource "google_compute_firewall" "allow_web_services" { 

    description = "Allow web services from the IP whitelist" 
    name    = "allow-web-services" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["80", "443", "8080", "8088", "8443", "8888"] 
    } 
    
    source_ranges = split(",", var.general.ip_whitelist) 
} 

resource "google_compute_firewall" "allow_splunk" { 

    description = "Allow Splunk services from the IP whitelist" 
    name    = "allow-splunk" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["8000", "8089", "9997"] 
    } 
    
    source_ranges = split(",", var.general.ip_whitelist) 
} 

resource "google_compute_firewall" "allow_grpc" { 

    description =  "Allow gRPC ports from the IP whitelistWinRM" 
    name    = "allow-grcp" 
    network = module.vpc.network_name 

    allow { 
        protocol = "tcp" 
        ports    = ["50051"] 
    } 
    
    source_ranges = split(",", var.general.ip_whitelist) 
} 

# Egress rule allowing all outbound traffic 
resource "google_compute_firewall" "default_egress" { 
    
    name    = "firewall-egress-${var.general.key_name}-${var.general.attack_range_name}" 
    network = module.vpc.network_name 

  allow {
    protocol = "all"
  }

  direction         = "EGRESS"
  destination_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "allow_internal_communication" {
    description = "Allow all internal communication within the 10.0.1.0/24 subnet"
    name    = "allow-internal-communication"
    network = module.vpc.network_name

    allow {
        protocol = "all"
    }

    source_ranges = ["10.0.1.0/24"]
}