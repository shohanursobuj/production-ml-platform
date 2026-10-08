{{- define "ml-api.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ml-api.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "ml-api.labels" -}}
{{ include "ml-api.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{/* Pod template shared by the Deployment and the Argo Rollout. */}}
{{- define "ml-api.podTemplate" -}}
metadata:
  labels:
    {{- include "ml-api.selectorLabels" . | nindent 4 }}
spec:
  serviceAccountName: {{ include "ml-api.fullname" . }}
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile: {type: RuntimeDefault}
  containers:
    - name: api
      image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
      imagePullPolicy: {{ .Values.image.pullPolicy }}
      ports:
        - {name: http, containerPort: 8080}
      env:
        {{- range $k, $v := .Values.env }}
        - {name: {{ $k }}, value: {{ $v | quote }}}
        {{- end }}
      readinessProbe:
        httpGet: {path: /readyz, port: http}
        periodSeconds: 5
      livenessProbe:
        httpGet: {path: /healthz, port: http}
        periodSeconds: 10
        failureThreshold: 3
      resources:
        {{- toYaml .Values.resources | nindent 8 }}
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: {drop: ["ALL"]}
      volumeMounts:
        - {name: tmp, mountPath: /tmp}
  volumes:
    - {name: tmp, emptyDir: {}}
{{- end -}}
