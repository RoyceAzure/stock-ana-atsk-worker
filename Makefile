PYTHON ?= python
BASH ?= bash
DB_SCRIPT := powershell -NoProfile -ExecutionPolicy Bypass -File

# kind-load-image tagging; override with APP_ENV=prod make kind-load-image
APP_ENV ?=dev
DOCKER_IMAGE ?= ghcr.io/royceazure/stock-ana-atsk-worker
DOCKER_TAG ?= $(APP_ENV)-latest
KIND_CLUSTER_NAME ?= kind-lab
K8S_SCRIPT := powershell -NoProfile -ExecutionPolicy Bypass -File .\deployment\scripts\k8s-local.ps1

.PHONY: run db-backup db-restore docker-login-ghcr docker-build docker-build-push-worker kind-load-image kind-init limit-workers k8s-namespace k8s-ghcr-secret k8s-gcp-sa-secret helm-install-postgres helm-migrate helm-install-worker helm-install-loki helm-install-promtail helm-install-grafana helm-install-metrics helm-install-logging helm-install-observability k8s-deploy-local k8s-deploy-all k8s-pg-port-forward k8s-grafana-port-forward grafana-port-forward k8s-undeploy k8s-undeploy-keep-pg k8s-undeploy-apps k8s-rollout-worker k8s-update-worker-image

# Run worker locally.
run:
	$(PYTHON) main.py --mode consumer

# Database backup / restore (PowerShell on Windows; bash elsewhere).
ifeq ($(OS),Windows_NT)
db-backup:
	$(DB_SCRIPT) .\script\db-backup.ps1

db-restore:
	$(DB_SCRIPT) .\script\db-restore.ps1
else
db-backup:
	$(BASH) script/db-backup.sh

db-restore:
	$(BASH) script/db-restore.sh
endif

# Docker / GHCR: load .env via k8s-local.ps1 (CRLF-safe on Windows).
docker-login-ghcr:
	$(K8S_SCRIPT) -Action docker-login-ghcr

docker-build:
	$(K8S_SCRIPT) -Action docker-build

docker-build-push-worker:
	$(K8S_SCRIPT) -Action docker-build-push-worker

# Load the local image into kind after docker-build.
kind-load-image:
	kind load docker-image $(DOCKER_IMAGE):$(DOCKER_TAG) --name $(KIND_CLUSTER_NAME)

kind-init:
	kind create cluster --config .\deployment\kind\init.yaml --name kind-lab

limit-workers:
	powershell -Command "docker update --cpus='2.0' --memory='2g' --memory-swap='2g' $$(docker ps --filter 'label=io.x-k8s.kind.role=worker' --format '{{.Names}}')"

# K8s targets use PowerShell so .env loading works on Windows.
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

# Restart worker pods so they re-pull image (e.g. after push to dev-latest).
k8s-rollout-worker:
	$(K8S_SCRIPT) -Action rollout-worker

# Build, push to GHCR, rollout restart worker (one-shot image update).
k8s-update-worker-image:
	$(K8S_SCRIPT) -Action update-worker-image

helm-install-promtail:
	$(K8S_SCRIPT) -Action helm-install-promtail

helm-install-loki:
	$(K8S_SCRIPT) -Action helm-install-loki

helm-install-logging:
	$(K8S_SCRIPT) -Action helm-install-logging

helm-install-observability:
	$(K8S_SCRIPT) -Action helm-install-observability

helm-install-grafana:
	$(K8S_SCRIPT) -Action helm-install-grafana

helm-install-metrics:
	$(K8S_SCRIPT) -Action helm-install-metrics

k8s-deploy-local:
	$(K8S_SCRIPT) -Action deploy

k8s-deploy-all:
	$(K8S_SCRIPT) -Action deploy-all

# Port-forward commands keep the terminal occupied.
k8s-pg-port-forward:
	$(K8S_SCRIPT) -Action pg-port-forward

k8s-grafana-port-forward grafana-port-forward:
	$(K8S_SCRIPT) -Action grafana-port-forward

# Uninstall Helm releases while keeping the Postgres PVC.
k8s-undeploy:
	$(K8S_SCRIPT) -Action undeploy-keep-pg

k8s-undeploy-keep-pg: k8s-undeploy

# Uninstall only worker and migration releases.
k8s-undeploy-apps:
	$(K8S_SCRIPT) -Action undeploy-apps
