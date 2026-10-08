variable "project_id" {
  description = "GCP project to deploy into."
  type        = string
}

variable "region" {
  description = "Region for all resources. Defaults to Frankfurt to keep data in the EU."
  type        = string
  default     = "europe-west3"
}

variable "cluster_name" {
  description = "GKE Autopilot cluster name."
  type        = string
  default     = "ml-platform"
}

variable "github_repository" {
  description = "owner/repo allowed to deploy via GitHub Actions OIDC (no long-lived keys)."
  type        = string
  default     = "shohanursobuj/production-ml-platform"
}
