## 8.
## OWASP Top 10 A8
## CSRF token enforcement example
## Enforce the presence of CSRF token in request header

resource "aws_wafregional_rule" "enforce_csrf" {
  name        = "${var.waf_prefix}-generic-enforce-csrf"
  metric_name = replace("${var.waf_prefix}genericenforcecsrf", "/[^0-9A-Za-z]/", "")

  dynamic "predicate" {
    for_each = var.rule_csrf_exclude_methods
    content {
      data_id = aws_wafregional_byte_match_set.exclude_csrf_method[predicate.value].id
      negated = true
      type    = "ByteMatch"
    }
  }

  dynamic "predicate" {
    for_each = var.rule_csrf_include_methods
    content {
      data_id = aws_wafregional_byte_match_set.include_csrf_method[predicate.value].id
      negated = false
      type    = "ByteMatch"
    }
  }

  predicate {
    data_id = aws_wafregional_size_constraint_set.csrf_token_set.id
    negated = true
    type    = "SizeConstraint"
  }

  predicate {
    data_id = aws_wafregional_byte_match_set.csrf_fetch_same_site.id
    negated = true
    type    = "ByteMatch"
  }

  predicate {
    data_id = aws_wafregional_byte_match_set.csrf_fetch_same_origin.id
    negated = true
    type    = "ByteMatch"
  }
}

resource "aws_wafregional_byte_match_set" "exclude_csrf_method" {
  for_each = toset(var.rule_csrf_exclude_methods)
  name     = "${var.waf_prefix}-generic-exclude-csrf-method-${each.value}"

  byte_match_tuples {
    text_transformation   = "LOWERCASE"
    target_string         = each.value
    positional_constraint = "EXACTLY"

    field_to_match {
      type = "METHOD"
    }
  }
}

resource "aws_wafregional_byte_match_set" "include_csrf_method" {
  for_each = toset(var.rule_csrf_include_methods)
  name     = "${var.waf_prefix}-generic-include-csrf-method-${each.value}"

  byte_match_tuples {
    text_transformation   = "LOWERCASE"
    target_string         = each.value
    positional_constraint = "EXACTLY"

    field_to_match {
      type = "METHOD"
    }
  }
}

resource "aws_wafregional_size_constraint_set" "csrf_token_set" {
  name = "${var.waf_prefix}-generic-match-csrf-token"

  size_constraints {
    text_transformation = "NONE"
    comparison_operator = "EQ"
    size                = "36"

    field_to_match {
      type = "HEADER"
      data = var.rule_csrf_header
    }
  }
}

resource "aws_wafregional_byte_match_set" "csrf_fetch_same_site" {
  name = "${var.waf_prefix}-generic-match-fetch-same-site"

  byte_match_tuples {
    text_transformation   = "LOWERCASE"
    target_string         = "same-site"
    positional_constraint = "EXACTLY"

    field_to_match {
      type = "HEADER"
      data = "sec-fetch-site"
    }
  }
}

resource "aws_wafregional_byte_match_set" "csrf_fetch_same_origin" {
  name = "${var.waf_prefix}-generic-match-fetch-same-origin"

  byte_match_tuples {
    text_transformation   = "LOWERCASE"
    target_string         = "same-origin"
    positional_constraint = "EXACTLY"

    field_to_match {
      type = "HEADER"
      data = "sec-fetch-site"
    }
  }
}

resource "aws_wafregional_size_constraint_set" "custom_csrf_token_set" {
  count = length(var.custom_csrf_token)

  name = "${var.waf_prefix}-${lower(var.custom_csrf_token[count.index].field)}-custom-csrf-token"

  size_constraints {
    text_transformation = "NONE"
    comparison_operator = var.custom_csrf_token[count.index].operator
    size                = var.custom_csrf_token[count.index].size

    field_to_match {
      type = "HEADER"
      data = var.custom_csrf_token[count.index].field
    }
  }
}