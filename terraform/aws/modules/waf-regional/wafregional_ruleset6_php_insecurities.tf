## 6.
## OWASP Top 10 A5
## PHP Specific Security Misconfigurations
## Matches request patterns designed to exploit insecure PHP/CGI configuration

resource "aws_wafregional_rule" "detect_php_insecure" {
  name        = "${var.waf_prefix}-generic-detect-php-insecure"
  metric_name = replace("${var.waf_prefix}genericdetectphpinsecure", "/[^0-9A-Za-z]/", "")

  predicate {
    data_id = aws_wafregional_byte_match_set.match_php_insecure_uri.id
    negated = false
    type    = "ByteMatch"
  }

  predicate {
    data_id = aws_wafregional_byte_match_set.match_php_insecure_var_refs.id
    negated = false
    type    = "ByteMatch"
  }
}

resource "aws_wafregional_byte_match_set" "match_php_insecure_uri" {
  name = "${var.waf_prefix}-generic-match-php-insecure-uri"

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "php"
    positional_constraint = "ENDS_WITH"

    field_to_match {
      type = "URI"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "/"
    positional_constraint = "ENDS_WITH"

    field_to_match {
      type = "URI"
    }
  }
}

resource "aws_wafregional_byte_match_set" "match_php_insecure_var_refs" {
  name = "${var.waf_prefix}-generic-match-php-insecure-var-refs"

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "_ENV["
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "auto_append_file="
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "disable_functions="
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "auto_prepend_file="
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "safe_mode="
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "_SERVER["
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "allow_url_include="
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "open_basedir="
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "QUERY_STRING"
    }
  }
}

