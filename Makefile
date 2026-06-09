kdin-init:
	kind create cluster --config .\depolyment\kind\inti.yaml --name kind-lab

limit-workers:
	powershell -Command "docker update --cpus='2.0' --memory='2g' --memory-swap='2g' $$(docker ps --filter 'label=io.x-k8s.kind.role=worker' --format '{{.Names}}')"
PHONY: kdin-init limit-workers
