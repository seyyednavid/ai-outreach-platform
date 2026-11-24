# Lightweight monitoring for the demo: two email alerts, nothing else.
#
#   1. "Backend unavailable": an uptime check calls /api/v1/health/ready
#      (API + database) every 5 minutes from 3 regions.
#   2. "Backend 5xx": any server error in a 5-minute window, from Cloud
#      Run's built-in request metric (no extra logging needed).
#
# Cost: uptime checks and Cloud Run metrics are inside the free tier;
# alerting is charged per condition (about $0.10/month each).

resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "AI Outreach alerts (email)"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }

  depends_on = [google_project_service.enabled["monitoring.googleapis.com"]]
}

resource "google_monitoring_uptime_check_config" "backend_ready" {
  project      = var.project_id
  display_name = "Backend ready (API + database)"

  # Every 5 minutes from 3 regions: about 26,000 checks a month, far
  # below the free 1 million. Each one is a tiny request to the backend.
  period           = "300s"
  timeout          = "10s"
  selected_regions = ["EUROPE", "USA_VIRGINIA", "USA_OREGON"]

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = trimprefix(local.backend_url, "https://")
    }
  }

  # /health/ready answers 200 only if the database answers too.
  http_check {
    path           = "/api/v1/health/ready"
    port           = 443
    use_ssl        = true
    validate_ssl   = true
    request_method = "GET"
    accepted_response_status_codes {
      status_class = "STATUS_CLASS_2XX"
    }
  }

  depends_on = [google_project_service.enabled["monitoring.googleapis.com"]]
}

resource "google_monitoring_alert_policy" "backend_unavailable" {
  project      = var.project_id
  display_name = "Backend unavailable"
  combiner     = "OR"

  conditions {
    display_name = "Health check failing from 2 or more regions"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
        "resource.type=\"uptime_url\"",
        "metric.label.check_id=\"${google_monitoring_uptime_check_config.backend_ready.uptime_check_id}\"",
      ])
      # Count the regions whose latest check failed; alert when more than
      # one fails for 5 minutes (one region alone can be a network blip).
      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.host"]
      }
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "300s"
      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }

  notification_channels = [google_monitoring_notification_channel.email.name]

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
      The backend's /api/v1/health/ready check is failing: the API is down
      or cannot reach the database (Supabase).

      1. Open ${local.backend_url}/api/v1/health/ready in a browser.
      2. Cloud Run > ai-outreach-backend > Logs: look for startup errors.
      3. Check the Supabase project is running (free projects pause when idle).
    EOT
  }
}

resource "google_monitoring_alert_policy" "backend_5xx" {
  project      = var.project_id
  display_name = "Backend 5xx errors"
  combiner     = "OR"

  conditions {
    display_name = "Any 5xx response in 5 minutes"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"run.googleapis.com/request_count\"",
        "resource.type=\"cloud_run_revision\"",
        "resource.label.service_name=\"${google_cloud_run_v2_service.backend.name}\"",
        "metric.label.response_code_class=\"5xx\"",
      ])
      # Demo traffic is low, so a single server error is worth an email.
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
      }
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"
      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }

  notification_channels = [google_monitoring_notification_channel.email.name]

  documentation {
    mime_type = "text/markdown"
    content   = <<-EOT
      The backend returned a server error (5xx).

      Logs Explorer, resource "Cloud Run Revision", service ai-outreach-backend,
      around the alert time: the request log shows the failing URL, and the
      application log shows the error.
    EOT
  }
}
