resource "aws_iam_role" "this" {
  name = "ar-${var.general.key_name}-${var.general.attack_range_name}-role"
  tags = {
    Name = "$ar-${var.general.key_name}-${var.general.attack_range_name}-role"
  }

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Action": "sts:AssumeRole",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Effect": "Allow",
    "Sid": ""
  }]
}
EOF
}

resource "aws_iam_instance_profile" "this" {
  name = "ar-${var.general.key_name}-${var.general.attack_range_name}-instance-profile"
  path = "/"
  role = aws_iam_role.this.name
}
