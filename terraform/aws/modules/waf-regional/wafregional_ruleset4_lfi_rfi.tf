## 4.
## OWASP Top 10 A4
## Path Traversal, LFI, RFI
## Matches request patterns designed to traverse filesystem paths, and include
## local or remote files

resource "aws_wafregional_rule" "detect_rfi_lfi_traversal" {
  name        = "${var.waf_prefix}-generic-detect-rfi-lfi-traversal"
  metric_name = replace("${var.waf_prefix}genericdetectrfilfitraversal", "/[^0-9A-Za-z]/", "")

  predicate {
    data_id = aws_wafregional_byte_match_set.match_rfi_lfi_traversal.id
    negated = false
    type    = "ByteMatch"
  }
}

resource "aws_wafregional_byte_match_set" "match_rfi_lfi_traversal" {
  name = "${var.waf_prefix}-generic-match-rfi-lfi-traversal"

  byte_match_tuples {
    text_transformation   = "HTML_ENTITY_DECODE"
    target_string         = "://"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "HTML_ENTITY_DECODE"
    target_string         = "../"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "://"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "../"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "HTML_ENTITY_DECODE"
    target_string         = "://"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "URI"
    }
  }

  byte_match_tuples {
    text_transformation   = "HTML_ENTITY_DECODE"
    target_string         = "../"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "URI"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "://"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "URI"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "../"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "URI"
    }
  }
}

