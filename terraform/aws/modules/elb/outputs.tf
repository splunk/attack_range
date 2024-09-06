output "arn" {
    description = "The Amazon Resource Name (ARN) of the load balancer."
    value       = aws_lb.main_elb[0].arn
}

output "dns_name" {
    description = "The DNS name of the load balancer."
    value       = aws_lb.main_elb[0].dns_name
}