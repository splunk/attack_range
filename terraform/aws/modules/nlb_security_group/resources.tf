resource "aws_security_group" "nlb" {
  name   = "sg_nlb_${var.general.key_name}_${var.general.attack_range_name}"
  vpc_id = var.aws.vpc_id
}

resource "aws_security_group_rule" "allow_inbound_splunkd" {
  type              = "ingress"
  from_port         = "9997"
  to_port           = "9997"
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.nlb.id
}

resource "aws_security_group_rule" "allow_inbound_hec" {
  type              = "ingress"
  from_port         = "8088"
  to_port           = "8088"
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.nlb.id
}

resource "aws_security_group_rule" "allow_inbound_syslog" {
  type              = "ingress"
  from_port         = "514"
  to_port           = "514"
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.nlb.id
}

resource "aws_security_group_rule" "allow_all_outbound" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.nlb.id
}
