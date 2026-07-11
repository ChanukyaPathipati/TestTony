variable "kubeconfig_path" {
  description = "Path to the kubeconfig used by Terraform and Helm."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Kubernetes context to deploy into. Set this to kind-ml-serving for the local quickstart, or null to use the current context."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Namespace for the serving application."
  type        = string
  default     = "ml-serving"
}

variable "monitoring_namespace" {
  description = "Namespace for Prometheus, Grafana, Loki, and Promtail."
  type        = string
  default     = "monitoring"
}

variable "image_repository" {
  description = "Container image repository for the serving app. For Kind, use ml-serving."
  type        = string
  default     = "ml-serving"
}

variable "image_tag" {
  description = "Container image tag for the serving app."
  type        = string
  default     = "local"
}

variable "image_pull_policy" {
  description = "Image pull policy for the serving app."
  type        = string
  default     = "IfNotPresent"
}

variable "ingress_nginx_values_file" {
  description = "Values file for ingress-nginx. Use my-webapp/nginx-kind-values.yaml locally and my-webapp/nginx-nlb-values.yaml on EKS."
  type        = string
  default     = "my-webapp/nginx-kind-values.yaml"
}
