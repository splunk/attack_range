## 2.
## OWASP Top 10 A2
## Blacklist bad/hijacked JWT tokens or session IDs
## Matches the specific values in the cookie or Authorization header
## for JWT it is sufficient to check the signature

resource "aws_wafregional_rule" "detect_bad_auth_tokens" {
  name        = "${var.waf_prefix}-generic-detect-bad-auth-tokens"
  metric_name = replace("${var.waf_prefix}genericdetectbadauthtokens", "/[^0-9A-Za-z]/", "")

  predicate {
    data_id = aws_wafregional_byte_match_set.match_auth_tokens.id
    negated = false
    type    = "ByteMatch"
  }
}

resource "aws_wafregional_byte_match_set" "match_auth_tokens" {
  name = "${var.waf_prefix}-generic-match-auth-tokens"

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = ".TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ"
    positional_constraint = "ENDS_WITH"

    field_to_match {
      type = "HEADER"
      data = "authorization"
    }
  }

  byte_match_tuples {
    text_transformation   = "URL_DECODE"
    target_string         = "example-session-id"
    positional_constraint = "CONTAINS"

    field_to_match {
      type = "HEADER"
      data = "cookie"
    }
  }
}

