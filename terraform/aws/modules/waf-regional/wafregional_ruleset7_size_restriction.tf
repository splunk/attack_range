## 7.
## OWASP Top 10 A7
## Mitigate abnormal requests via size restrictions
## Enforce consistent request hygene, limit size of key elements

resource "aws_wafregional_rule" "restrict_sizes" {
  name        = "${var.waf_prefix}-generic-restrict-sizes"
  metric_name = replace("${var.waf_prefix}genericrestrictsizes", "/[^0-9A-Za-z]/", "")

  predicate {
    data_id = aws_wafregional_size_constraint_set.size_restrictions.id
    negated = false
    type    = "SizeConstraint"
  }
}

resource "aws_wafregional_size_constraint_set" "size_restrictions" {
  name = "${var.waf_prefix}-generic-size-restrictions"

  #
  # Note: we are disabling this constraint because uploads will be affected.
  #
  # size_constraints {
  #   text_transformation = "NONE"
  #   comparison_operator = "GT"
  #   size                = "4096"
  #
  #   field_to_match {
  #     type = "BODY"
  #   }
  # }

  size_constraints {
    text_transformation = "NONE"
    comparison_operator = "GT"
    size                = "4093"

    field_to_match {
      type = "HEADER"
      data = "cookie"
    }
  }
  size_constraints {
    text_transformation = "NONE"
    comparison_operator = "GT"
    size                = "1024"

    field_to_match {
      type = "QUERY_STRING"
    }
  }
  size_constraints {
    text_transformation = "NONE"
    comparison_operator = "GT"
    size                = "512"

    field_to_match {
      type = "URI"
    }
  }
}

