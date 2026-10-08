output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "cluster_name" {
  value = google_container_cluster.ml.name
}

output "workload_identity_provider" {
  description = "Set as GCP_WORKLOAD_IDENTITY_PROVIDER in GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  description = "Set as GCP_DEPLOYER_SA in GitHub Actions."
  value       = google_service_account.deployer.email
}
