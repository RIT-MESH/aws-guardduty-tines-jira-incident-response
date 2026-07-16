# Amazon GuardDuty detector.
#
# GuardDuty publishes findings to Amazon EventBridge; this detector is the
# source of the findings that the rest of the workflow consumes.
# See: https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html

resource "aws_guardduty_detector" "this" {
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }

  tags = {
    Name = "${local.name_prefix}-detector"
  }
}
