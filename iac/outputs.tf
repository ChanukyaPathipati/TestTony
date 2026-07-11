output "application_url" {
  description = "Local URL when using Kind/Minikube port-forwarding or localhost ingress."
  value       = "http://localhost"
}

output "application_namespace" {
  description = "Namespace containing the serving application."
  value       = var.namespace
}

output "grafana_port_forward" {
  description = "Command to open the monitoring dashboard locally."
  value       = "kubectl -n ${var.monitoring_namespace} port-forward svc/kube-prom-stack-grafana 3000:80"
}

output "prometheus_port_forward" {
  description = "Command to open Prometheus locally."
  value       = "kubectl -n ${var.monitoring_namespace} port-forward svc/kube-prom-stack-kube-prome-prometheus 9090:9090"
}
