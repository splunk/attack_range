resource "aws_security_group" "edge-processor" {
  name   = "sg_edge_processor_${var.general.key_name}_${var.general.attack_range_name}"
  vpc_id = var.aws.vpc_id
}

resource "aws_security_group_rule" "allow_all_outbound" {
  description       = "Outgoing traffic"
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.edge-processor.id
}

resource "aws_security_group_rule" "allow_ssh_from_bastion_host" {
  description              = "SSH from bastion host"
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = var.bastion_host_security_group_id
  security_group_id        = aws_security_group.edge-processor.id
}

resource "aws_security_group_rule" "allow_lb_syslog_inbound" {
  description              = "syslog inbound from load balancer"
  type                     = "ingress"
  from_port                = 514
  to_port                  = 514
  protocol                 = "tcp"
  source_security_group_id = var.nlb_security_group_id
  security_group_id        = aws_security_group.edge-processor.id
}

resource "aws_security_group_rule" "allow_lb_splunkd_inbound" {
  description              = "splunkd inbound from load balancer"
  type                     = "ingress"
  from_port                = 9997
  to_port                  = 9997
  protocol                 = "tcp"
  source_security_group_id = var.nlb_security_group_id
  security_group_id        = aws_security_group.edge-processor.id
}

resource "aws_security_group_rule" "allow_lb_hec_inbound" {
  description              = "HEC inbound from load balancer"
  type                     = "ingress"
  from_port                = 8088
  to_port                  = 8088
  protocol                 = "tcp"
  source_security_group_id = var.nlb_security_group_id
  security_group_id        = aws_security_group.edge-processor.id
}

