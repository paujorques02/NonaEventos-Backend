provider "google" {
  credentials = file("<PATH_TO_YOUR_SERVICE_ACCOUNT_JSON>")
  project     = var.project_id
  region      = var.region
}

resource "google_firestore_database" "chatbot_db" {
  name     = "chatbot-database"
  project  = var.project_id
  location = var.region
}

resource "google_project" "chatbot_project" {
  name       = var.project_name
  project_id = var.project_id
  org_id     = var.organization_id
  billing_account = var.billing_account_id
}

resource "google_storage_bucket" "chatbot_bucket" {
  name     = "${var.project_id}-bucket"
  location = var.region
  uniform_bucket_level_access = true
}

output "firestore_database_url" {
  value = google_firestore_database.chatbot_db.id
}

output "storage_bucket_url" {
  value = google_storage_bucket.chatbot_bucket.url
}

output "project_id" {
  value = google_project.chatbot_project.project_id
}