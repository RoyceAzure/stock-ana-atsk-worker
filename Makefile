GHCR_SECRET_NAME ?= ghcr-secret
HELM_CHART_POSTGRES := ./deployment/helm/charts/postgres
HELM_CHART_DB_MIGRATE := ./deployment/helm/charts/db-migrate
K8S_SCRIPT := powershell -NoProfile -ExecutionPolicy Bypass -File .\deployment\scripts\k8s-local.ps1

.PHONY: kind-init limit-workers k8s-namespace k8s-ghcr-secret helm-install-postgres helm-migrate k8s-deploy-local k8s-pg-port-forward k8s-undeploy-postgres

kind-init:
	kind create cluster --config .\deployment\kind\init.yaml --name kind-lab

limit-workers:
	powershell -Command "docker update --cpus='2.0' --memory='2g' --memory-swap='2g' $$(docker ps --filter 'label=io.x-k8s.kind.role=worker' --format '{{.Names}}')"

# 以下 k8s targets 透過 PowerShell 讀取 .env（Windows 相容）
k8s-namespace:
	$(K8S_SCRIPT) -Action namespace

k8s-ghcr-secret:
	$(K8S_SCRIPT) -Action ghcr-secret

helm-install-postgres:
	$(K8S_SCRIPT) -Action helm-install

helm-migrate:
	$(K8S_SCRIPT) -Action helm-migrate

k8s-deploy-local:
	$(K8S_SCRIPT) -Action deploy

# 本機連線 Postgres（會佔用終端，請另開視窗執行）
k8s-pg-port-forward:
	$(K8S_SCRIPT) -Action pg-port-forward

k8s-undeploy-postgres:
	$(K8S_SCRIPT) -Action undeploy
