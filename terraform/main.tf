provider "aws" {
  profile    = var.aws_profile
  region     = var.aws_region
}

resource "random_pet" "server" {
}

resource "aws_instance" "splunk-server" {
  ami           = var.splunk_ami
  instance_type = "t2.xlarge"
  tags = {
    Name = "splunk-server-${random_pet.server.id}"
  }
}

resource "aws_eip" "ip" {
  instance = aws_instance.splunk-server.id
}
