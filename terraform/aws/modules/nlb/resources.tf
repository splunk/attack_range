resource "aws_lb" "main_nlb" {
  count                                                        = var.edge_processor.use_nlb == "1" ? 1 : 0
  name                                                         = "ar-nlb-${var.general.key_name}-${var.general.attack_range_name}"
  internal                                                     = true # Set to true for internal/private NLB
  load_balancer_type                                           = "network"
  dns_record_client_routing_policy                             = "availability_zone_affinity"
  security_groups                                              = [var.nlb_security_group_id]
  subnets                                                      = [var.ec2_subnet_id, var.aws.alt_subnet_id]
  enable_deletion_protection                                   = false
  enable_cross_zone_load_balancing                             = true
  enforce_security_group_inbound_rules_on_private_link_traffic = "off"
}

resource "aws_lb_target_group" "main_splunkd_tg" {
  count    = var.edge_processor.use_nlb == "1" ? 1 : 0
  port     = 9997
  protocol = "TCP"
  vpc_id   = var.aws.vpc_id

  tags = {
    Name = "ar-nlb-${var.general.key_name}-${var.general.attack_range_name}"
  }
}

resource "aws_lb_listener" "main_nlb_splunkd" {
  count             = var.edge_processor.use_nlb == "1" ? 1 : 0
  load_balancer_arn = aws_lb.main_nlb[count.index].arn
  port              = "9997"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main_splunkd_tg[count.index].arn
  }
}

resource "aws_lb_target_group" "main_hec_tg" {
  count    = var.edge_processor.use_nlb == "1" ? 1 : 0
  port     = 8088
  protocol = "TCP"
  vpc_id   = var.aws.vpc_id

  tags = {
    Name = "${var.general.key_name}_${var.general.attack_range_name}-hec-tg"
  }
}

resource "aws_lb_listener" "main_nlb_hec" {
  count             = var.edge_processor.use_nlb == "1" ? 1 : 0
  load_balancer_arn = aws_lb.main_nlb[count.index].arn
  port              = "8088"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main_hec_tg[count.index].arn
  }
}

resource "aws_lb_target_group" "main_syslog_tg" {
  count    = var.edge_processor.use_nlb == "1" ? 1 : 0
  port     = 514
  protocol = "TCP"
  vpc_id   = var.aws.vpc_id

  tags = {
    Name = "${var.general.key_name}_${var.general.attack_range_name}-syslog-tg"
  }
}

resource "aws_lb_listener" "main_nlb_syslog" {
  count             = var.edge_processor.use_nlb == "1" ? 1 : 0
  load_balancer_arn = aws_lb.main_nlb[count.index].arn
  port              = "514"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main_syslog_tg[count.index].arn
  }
}

