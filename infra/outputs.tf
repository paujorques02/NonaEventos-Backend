output "firestore_url" {
  value = google_firestore_database.default.id
}

output "project_id" {
  value = google_project.project.project_id
}

output "region" {
  value = var.region
}

output "service_account_email" {
  value = google_service_account.default.email
}