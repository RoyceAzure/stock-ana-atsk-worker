{{- define "task-worker.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "task-worker.fullname" -}}
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

{{- define "task-worker.labels" -}}
helm.sh/chart: {{ include "task-worker.chart" . }}
{{ include "task-worker.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "task-worker.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "task-worker.selectorLabels" -}}
app.kubernetes.io/name: {{ include "task-worker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: task-worker
{{- end }}

{{- define "task-worker.pgHost" -}}
{{- printf "%s-postgres" .Values.postgres.releaseName }}
{{- end }}

{{- define "task-worker.pgSecretName" -}}
{{- .Values.postgres.secretName | default (printf "%s-postgres-secret" .Values.postgres.releaseName) }}
{{- end }}

{{- define "task-worker.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "task-worker.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "task-worker.useGcpSaJson" -}}
{{- eq (.Values.gcp.authMode | lower) "service_account_json" -}}
{{- end }}
