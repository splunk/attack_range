## 5.
## OWASP Top 10 A4
## Privileged Module Access Restrictions
## Restrict access to the admin interface to known source IPs only
## Matches the URI prefix, when the remote IP isn't in the whitelist

resource "aws_wafregional_rule" "detect_admin_access" {
  name        = "${var.waf_prefix}-generic-detect-admin-access"
  metric_name = replace("${var.waf_prefix}genericdetectadminaccess", "/[^0-9A-Za-z]/", "")

  predicate {
    data_id = aws_wafregional_ipset.admin_remote_ipset.id
    negated = true
    type    = "IPMatch"
  }

  predicate {
    data_id = aws_wafregional_byte_match_set.match_admin_url.id
    negated = false
    type    = "ByteMatch"
  }
}

resource "aws_wafregional_ipset" "admin_remote_ipset" {
  name = "${var.waf_prefix}-generic-match-admin-remote-ip"
  dynamic "ip_set_descriptor" {
    for_each = var.admin_remote_ipset

    content {
      type  = "IPV4"
      value = ip_set_descriptor.value
    }
  }
}

resource "aws_wafregional_byte_match_set" "match_admin_url" {
  name = "${var.waf_prefix}-generic-match-admin-url"

  dynamic "byte_match_tuples" {
    for_each = var.rule_admin_path_constraints

    content {
      text_transformation   = "URL_DECODE"
      target_string         = byte_match_tuples.value.target_string
      positional_constraint = byte_match_tuples.value.positional_constraint

      field_to_match {
        type = "URI"
      }
    }
  }
}
