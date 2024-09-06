resource "aws_security_group" "apache-httpd" {
  name   = "sg_httpd_processor_${var.general.key_name}_${var.general.attack_range_name}"
  vpc_id = var.aws.vpc_id
}

resource "aws_security_group_rule" "allow_all_outbound" {
  description       = "Outgoing traffic"
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.apache-httpd.id
}

resource "aws_security_group_rule" "allow_ssh_from_bastion_host" {
  description              = "SSH from bastion host"
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = var.bastion_host_security_group_id
  security_group_id        = aws_security_group.apache-httpd.id
}

resource "aws_security_group_rule" "allow_lb_http_inbound" {
  description = "http inbound from load balancer"
  type        = "ingress"
  from_port   = 80
  to_port     = 80
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  # source_security_group_id = var.elb_security_group_id
  security_group_id = aws_security_group.apache-httpd.id
}

resource "aws_security_group_rule" "allow_lb_https_inbound" {
  description = "https inbound from load balancer"
  type        = "ingress"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  # source_security_group_id = var.elb_security_group_id
  security_group_id = aws_security_group.apache-httpd.id
}
