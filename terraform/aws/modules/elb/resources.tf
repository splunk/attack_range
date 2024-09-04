data "aws_acm_certificate" "cert" {
  domain = var.httpd_server.domain
}


resource "aws_lb" "main_elb" {
  count = var.httpd_server.use_alb == "1" ? 1 : 0

  internal                         = true
  enable_cross_zone_load_balancing = true
  idle_timeout                     = "60"
  load_balancer_type               = "application"

  security_groups            = [var.elb_security_group_id]
  subnets                    = [var.ec2_subnet_id, var.aws.alt_subnet_id]
  enable_deletion_protection = false

  tags = {
    Name = "ar-${var.general.key_name}_${var.general.attack_range_name}-elb"
  }
}

#############################
# this covers HTTPS traffic #
#############################
resource "aws_lb_target_group" "main_https_tg" {
  count    = var.httpd_server.use_alb == "1" ? 1 : 0
  port     = 443
  protocol = "HTTPS"
  vpc_id   = var.aws.vpc_id

  health_check {
    protocol            = "HTTPS"
    path                = "/services/collector/health/1.0"
    interval            = "15"
    healthy_threshold   = "2"
    unhealthy_threshold = "2"
    timeout             = "5"
  }

  tags = {
    Name = "ar-${var.general.key_name}_${var.general.attack_range_name}-https-tg"
  }
}

resource "aws_lb_target_group_attachment" "apache-httpd_https" {
  count            = var.httpd_server.use_alb == "1" ? 1 : 0
  target_group_arn = aws_lb_target_group.main_https_tg[count.index].arn
  target_id        = var.apache-httpd_instance_id
}

resource "aws_lb_listener" "main_elb_https" {
  count             = var.httpd_server.use_alb == "1" ? 1 : 0
  load_balancer_arn = aws_lb.main_elb[count.index].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = data.aws_acm_certificate.cert.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main_https_tg[count.index].arn
  }
}

###########################
# This covers HTTP traffic #
###########################
resource "aws_lb_target_group" "main_http_tg" {
  count    = var.httpd_server.use_alb == "1" ? 1 : 0
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.aws.vpc_id

  health_check {
    protocol            = "HTTP"
    path                = "/services/collector/health/1.0"
    interval            = "15"
    healthy_threshold   = "2"
    unhealthy_threshold = "2"
    timeout             = "5"
    port                = "80"
  }

  tags = {
    Name = "ar-${var.general.key_name}_${var.general.attack_range_name}-http-tg"
  }
}

resource "aws_lb_target_group_attachment" "apache-httpd_http" {
  count            = var.httpd_server.use_alb == "1" ? 1 : 0
  target_group_arn = aws_lb_target_group.main_http_tg[count.index].arn
  target_id        = var.apache-httpd_instance_id
}

resource "aws_lb_listener" "main_elb_http" {
  count             = var.httpd_server.use_alb == "1" ? 1 : 0
  load_balancer_arn = aws_lb.main_elb[count.index].arn
  port              = "80"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main_http_tg[count.index].arn
  }
}

