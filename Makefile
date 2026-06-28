PYTHON ?= python

# Windows：避免 PATH 的 bash 指向 WSL；使用 Git Bash 以共用 Windows 的 aws / psql / localhost port-forward
ifeq ($(OS),Windows_NT)
BASH := "C:/Program Files/Git/bin/bash.exe"
else
BASH := bash
endif

GHCR_SECRET_NAME ?= ghcr-secret
DOCKER_IMAGE ?= ghcr.io/royceazure/stock-ana-atsk-worker
DOCKER_TAG ?= dev-latest
DOCKERFILE := deployment/docker/Dockerfile
KIND_CLUSTER_NAME ?= kind-lab
HELM_CHART_POSTGRES := ./deployment/helm/charts/postgres
HELM_CHART_DB_MIGRATE := ./deployment/helm/charts/db-migrate
HELM_CHART_TASK_WORKER := ./deployment/helm/charts/task-worker
HELM_CHART_PROMTAIL := ./deployment/helm/charts/promtail
HELM_CHART_LOKI := ./deployment/helm/charts/loki
K8S_SCRIPT := powershell -NoProfile -ExecutionPolicy Bypass -File .\deployment\scripts\k8s-local.ps1

.PHONY: run db-backup db-restore docker-build kind-load-image kind-init limit-workers k8s-namespace k8s-ghcr-secret k8s-gcp-sa-secret helm-install-postgres helm-migrate helm-install-worker helm-install-loki helm-install-promtail helm-install-logging k8s-deploy-local k8s-deploy-all k8s-pg-port-forward k8s-undeploy k8s-undeploy-keep-pg k8s-undeploy-apps

# 本機啟動 worker（讀取 .env / 環境變數）
run:
	$(PYTHON) main.py --mode consumer

# DB 備份 / 還原（讀取 script/.env；Windows 透過 Git Bash 執行）
db-backup:
	$(BASH) script/db-backup.sh

db-restore:
	$(BASH) script/db-restore.sh

# 建置 worker 映像（專案根目錄執行）
docker-build:
	docker build -f $(DOCKERFILE) -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

# kind 載入本機映像（需先 make docker-build）
kind-load-image:
	kind load docker-image $(DOCKER_IMAGE):$(DOCKER_TAG) --name $(KIND_CLUSTER_NAME)

kind-init:
	kind create cluster --config .\deployment\kind\init.yaml --name kind-lab

limit-workers:
	powershell -Command "docker update --cpus='2.0' --memory='2g' --memory-swap='2g' $$(docker ps --filter 'label=io.x-k8s.kind.role=worker' --format '{{.Names}}')"

# 以下 k8s targets 透過 PowerShell 讀取 .env（Windows 相容）
k8s-namespace:
	$(K8S_SCRIPT) -Action namespace

k8s-ghcr-secret:
	$(K8S_SCRIPT) -Action ghcr-secret

k8s-gcp-sa-secret:
	$(K8S_SCRIPT) -Action gcp-sa-secret

helm-install-postgres:
	$(K8S_SCRIPT) -Action helm-install

helm-migrate:
	$(K8S_SCRIPT) -Action helm-migrate

helm-install-worker:
	$(K8S_SCRIPT) -Action helm-install-worker

helm-install-promtail:
	$(K8S_SCRIPT) -Action helm-install-promtail

helm-install-loki:
	$(K8S_SCRIPT) -Action helm-install-loki

helm-install-logging:
	$(K8S_SCRIPT) -Action helm-install-logging

k8s-deploy-local:
	$(K8S_SCRIPT) -Action deploy

k8s-deploy-all:
	$(K8S_SCRIPT) -Action deploy-all

# 本機連線 Postgres（會佔用終端，請另開視窗執行）
k8s-pg-port-forward:
	$(K8S_SCRIPT) -Action pg-port-forward

# 卸載全部 Helm release（worker + migrate + postgres），保留 Postgres PVC 資料
k8s-undeploy:
	$(K8S_SCRIPT) -Action undeploy-keep-pg

k8s-undeploy-keep-pg: k8s-undeploy

# 僅卸載 worker + migrate，Postgres 與其 volume 維持運行
k8s-undeploy-apps:
	$(K8S_SCRIPT) -Action undeploy-apps
