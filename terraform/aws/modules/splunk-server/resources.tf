data "aws_ami" "splunk_server" {
  count       = (var.splunk_server.byo_splunk == "0") ? 1 : 0
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_iam_role" "splunk_role" {
  count = ((var.aws.cloudtrail == "1") || (var.general.carbon_black_cloud == "1")) && (var.splunk_server.byo_splunk == "0") ? 1 : 0
  name = "splunk_role_${var.general.key_name}_${var.general.attack_range_name}"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

}

resource "aws_iam_instance_profile" "splunk_profile" {
  count = ((var.aws.cloudtrail == "1") || (var.general.carbon_black_cloud == "1")) && (var.splunk_server.byo_splunk == "0") ? 1 : 0
  name = "splunk_profile_${var.general.key_name}_${var.general.attack_range_name}"
  role = aws_iam_role.splunk_role[0].name
}


data "aws_iam_policy_document" "splunk_logging" {
  count = ((var.aws.cloudtrail == "1") || (var.general.carbon_black_cloud == "1")) && (var.splunk_server.byo_splunk == "0") ? 1 : 0

  statement {
    actions = [
      "sqs:GetQueueAttributes",
      "sqs:ListQueues",
      "sqs:ReceiveMessage",
      "sqs:GetQueueUrl",
      "sqs:DeleteMessage",
      "s3:Get*",
      "s3:List*",
      "s3:Delete*",
      "kms:Decrypt",
    ]

    resources = [
      "*"
    ]
  }
}

resource "aws_iam_role_policy" "splunk_logging_policy" {
  count = ((var.aws.cloudtrail == "1") || (var.general.carbon_black_cloud == "1")) && (var.splunk_server.byo_splunk == "0") ? 1 : 0
  name = "splunk_logging_policy_${var.general.key_name}_${var.general.attack_range_name}"
  role = aws_iam_role.splunk_role[0].id
  policy = data.aws_iam_policy_document.splunk_logging[0].json
}


resource "aws_instance" "splunk-server" {
  count                  = var.splunk_server.byo_splunk == "0" ? 1 : 0
  ami                    = data.aws_ami.splunk_server[0].id
  instance_type          = "t3.2xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.12"
  iam_instance_profile   = ((var.aws.cloudtrail == "1") || (var.general.carbon_black_cloud == "1")) && (var.splunk_server.byo_splunk == "0") ? aws_iam_instance_profile.splunk_profile[0].name : null
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp2"
    volume_size = "120"
    delete_on_termination = "true"
  }

  tags = {
    Name = "ar-splunk-${var.general.key_name}-${var.general.attack_range_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = self.public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      cat <<EOF > vars/splunk_vars.json
      {
        "ansible_python_interpreter": "/usr/bin/python3",
        "general": ${jsonencode(var.general)},
        "aws": ${jsonencode(var.aws)},
        "splunk_server": ${jsonencode(var.splunk_server)},
        "phantom_server": ${jsonencode(var.phantom_server)},
        "simulation": ${jsonencode(var.simulation)},
        "kali_server": ${jsonencode(var.kali_server)},
        "zeek_server": ${jsonencode(var.zeek_server)},
        "windows_servers": ${jsonencode(var.windows_servers)},
        "linux_servers": ${jsonencode(var.linux_servers)},
        "snort_server": ${jsonencode(var.snort_server)}
      }
      EOF
    EOT
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key '${var.aws.private_key_path}' -i '${self.public_ip},' splunk_server.yml -e "@vars/splunk_vars.json"
    EOT
  }

}

resource "aws_eip" "splunk_ip" {
  count = (var.splunk_server.byo_splunk == "0") && (var.aws.use_elastic_ips == "1") ? 1 : 0
  instance = aws_instance.splunk-server[0].id
}