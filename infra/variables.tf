variable "project_id" {
  description = "The ID of the Google Cloud project"
  type        = string
}

variable "region" {
  description = "The region where resources will be deployed"
  type        = string
  default     = "us-central1"
}

variable "firestore_database_id" {
  description = "The ID of the Firestore database"
  type        = string
}

variable "google_credentials" {
  description = "Path to the Google Cloud service account key file"
  type        = string
}