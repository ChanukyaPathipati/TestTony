resource "kubernetes_namespace" "app" {
  metadata {
    name = var.namespace
  }
}

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = var.monitoring_namespace
  }
}

resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  version          = "4.10.1"
  namespace        = "ingress-nginx"
  create_namespace = true

  values = [file("${path.module}/${var.ingress_nginx_values_file}")]
}

resource "helm_release" "monitoring" {
  name       = "kube-prom-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "56.7.0"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name

  values = [file("${path.module}/monitoring/prometheus-values.yaml")]
}

resource "helm_release" "loki_stack" {
  name       = "loki-stack"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki-stack"
  version    = "2.10.2"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name

  values = [file("${path.module}/monitoring/loki-stack-values.yaml")]
}

resource "kubernetes_config_map" "grafana_dashboard" {
  metadata {
    name      = "ml-serving-dashboard"
    namespace = kubernetes_namespace.monitoring.metadata[0].name
    labels = {
      grafana_dashboard = "1"
    }
  }

  data = {
    "ml-serving-dashboard.json" = file("${path.module}/monitoring/ml-serving-dashboard.json")
  }

  depends_on = [helm_release.monitoring]
}

resource "helm_release" "serving_app" {
  name      = "ml-serving"
  chart     = "${path.module}/my-webapp"
  namespace = kubernetes_namespace.app.metadata[0].name

  set {
    name  = "image.repository"
    value = var.image_repository
  }

  set {
    name  = "image.tag"
    value = var.image_tag
  }

  set {
    name  = "image.pullPolicy"
    value = var.image_pull_policy
  }

  set {
    name  = "serviceMonitor.namespace"
    value = var.monitoring_namespace
  }

  depends_on = [helm_release.ingress_nginx, helm_release.monitoring, helm_release.loki_stack]
}
