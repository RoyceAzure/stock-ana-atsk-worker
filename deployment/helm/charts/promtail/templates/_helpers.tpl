{{- define "promtail.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "promtail.fullname" -}}
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

{{- define "promtail.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "promtail.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app: promtail
{{- end }}

{{- define "promtail.selectorLabels" -}}
app.kubernetes.io/name: {{ include "promtail.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: promtail
{{- end }}

{{- define "promtail.jsonAppSelector" -}}
{{- $apps := .Values.pipeline.jsonApps -}}
{{- if not $apps -}}
task-worker
{{- else -}}
{{- join "|" $apps -}}
{{- end -}}
{{- end }}
