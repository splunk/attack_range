data "aws_route53_zone" "existing" {
  name         = var.dns_zone
  vpc_id       = var.vpc_id
  private_zone = true
}

resource "aws_route53_zone" "private" {
  count = data.aws_route53_zone.existing.zone_id == null ? 1 : 0

  name = var.dns_zone
  vpc {
    vpc_id = var.vpc_id
  }
}

data "aws_route53_zone" "private" {
  zone_id      = try(aws_route53_zone.private[0].zone_id, data.aws_route53_zone.existing.zone_id)
  private_zone = true
}
