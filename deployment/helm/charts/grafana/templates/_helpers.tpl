{{- define "grafana.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "grafana.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "grafana.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "grafana.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app: grafana
{{- end }}

{{- define "grafana.selectorLabels" -}}
app.kubernetes.io/name: {{ include "grafana.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: grafana
{{- end }}

{{- define "grafana.lokiUrl" -}}
http://{{ .Values.loki.serviceName }}.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.loki.port }}
{{- end }}

{{- define "grafana.dashboardNamespace" -}}
{{- default .Release.Namespace .Values.dashboards.defaultNamespace -}}
{{- end }}

{{- define "grafana.workerPodRegex" -}}
{{- if .Values.dashboards.worker.podRegex -}}
{{- .Values.dashboards.worker.podRegex -}}
{{- else -}}
.*-worker-.*
{{- end -}}
{{- end }}

{{- define "grafana.prometheusUrl" -}}
http://{{ .Values.prometheus.serviceName }}.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.prometheus.port }}
{{- end }}
