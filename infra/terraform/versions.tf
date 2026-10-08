terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # State lives in GCS; pass the bucket at init time:
  #   terraform init -backend-config="bucket=<state-bucket>"
  backend "gcs" {
    prefix = "production-ml-platform"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
