provider "aws" {
  profile    = var.aws_profile
  region     = var.aws_region
}

resource "aws_instance" "splunk-server" {
  ami           = var.splunk_ami
  instance_type = "t2.xlarge"
  tags = {
    Name = "attack-range_splunk-server"
  }
}

resource "aws_eip" "ip" {
  instance = aws_instance.splunk-server.id
}
