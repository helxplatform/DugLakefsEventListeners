{{- define "listener.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "listener.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "listener.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "listener.labels" -}}
app.kubernetes.io/name: {{ include "listener.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "listener.selectorLabels" -}}
app.kubernetes.io/name: {{ include "listener.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "listener.hookSecretName" -}}
{{- if .Values.hook.existingSecret -}}
{{- .Values.hook.existingSecret -}}
{{- else -}}
{{- printf "%s-hook-token" (include "listener.fullname" .) -}}
{{- end -}}
{{- end -}}
