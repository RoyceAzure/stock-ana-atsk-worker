{{- define "metrics.chart" -}}
{{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "metrics.prometheus.fullname" -}}
{{- default "prometheus" .Values.prometheus.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "metrics.prometheus.labels" -}}
helm.sh/chart: {{ include "metrics.chart" . }}
app.kubernetes.io/name: prometheus
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app: prometheus
{{- end }}

{{- define "metrics.prometheus.selectorLabels" -}}
app.kubernetes.io/name: prometheus
app.kubernetes.io/instance: {{ .Release.Name }}
app: prometheus
{{- end }}

{{- define "metrics.nodeExporter.fullname" -}}
{{- default "node-exporter" .Values.nodeExporter.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "metrics.nodeExporter.labels" -}}
helm.sh/chart: {{ include "metrics.chart" . }}
app.kubernetes.io/name: node-exporter
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app: node-exporter
{{- end }}

{{- define "metrics.nodeExporter.selectorLabels" -}}
app.kubernetes.io/name: node-exporter
app.kubernetes.io/instance: {{ .Release.Name }}
app: node-exporter
{{- end }}

{{- define "metrics.kubeStateMetrics.fullname" -}}
{{- default "kube-state-metrics" .Values.kubeStateMetrics.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "metrics.kubeStateMetrics.labels" -}}
helm.sh/chart: {{ include "metrics.chart" . }}
app.kubernetes.io/name: kube-state-metrics
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app: kube-state-metrics
{{- end }}

{{- define "metrics.kubeStateMetrics.selectorLabels" -}}
app.kubernetes.io/name: kube-state-metrics
app.kubernetes.io/instance: {{ .Release.Name }}
app: kube-state-metrics
{{- end }}

{{- define "metrics.scrapeNamespaceRegex" -}}
{{- if .Values.scrapeNamespaces -}}
{{- join "|" .Values.scrapeNamespaces -}}
{{- end -}}
{{- end }}
