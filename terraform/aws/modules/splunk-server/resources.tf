

data "aws_ami" "splunk_server" {
  most_recent = true
  owners      = ["self"] 

  filter {
    name   = "name"
    values = [var.splunk_server.image]
  }
}


resource "aws_iam_role" "splunk_role" {
  name = "splunk_role_${var.general.key_name}"

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
  name = "splunk_profile_${var.general.key_name}"
  role = aws_iam_role.splunk_role.name
}


data "aws_iam_policy_document" "splunk_logging" {

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
  count = (var.aws.cloudtrail == "1") || (var.general.carbon_black_cloud == "1")  ? 1 : 0
  name = "splunk_logging_policy_${var.general.key_name}"
  role = aws_iam_role.splunk_role.id
  policy = data.aws_iam_policy_document.splunk_logging.json
}


resource "aws_instance" "splunk-server" {
  ami                    = data.aws_ami.splunk_server.id
  instance_type          = "t3.2xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.12"
  iam_instance_profile   = aws_iam_instance_profile.splunk_profile.name

  root_block_device {
    volume_type = "gp2"
    volume_size = "60"
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
      host        = aws_instance.splunk-server.public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.aws.private_key_path} -i '${aws_instance.splunk-server.public_ip},' splunk_server_post.yml -e 'ansible_python_interpreter=/usr/bin/python3 ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.aws : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.phantom_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.simulation : "${key}=\"${value}\""])}'"
  }

}

resource "aws_eip" "splunk_ip" {
  instance = aws_instance.splunk-server.id
}
