.PHONY: demo train evaluate deploy predict monitor rollback health minikube-up kubernetes-plan test clean

demo:
	PYTHONPATH=src python3 -m kube_mlops_platform demo --output .local

train:
	PYTHONPATH=src python3 -m kube_mlops_platform train --output .local

evaluate:
	PYTHONPATH=src python3 -m kube_mlops_platform evaluate --output .local

deploy:
	PYTHONPATH=src python3 -m kube_mlops_platform deploy --output .local

predict:
	PYTHONPATH=src python3 -m kube_mlops_platform predict --output .local

monitor:
	PYTHONPATH=src python3 -m kube_mlops_platform monitor --output .local

rollback:
	PYTHONPATH=src python3 -m kube_mlops_platform rollback --output .local

health:
	PYTHONPATH=src python3 -m kube_mlops_platform health --output .local

minikube-up:
	@echo "Start Minikube and install KServe, then apply manifests:"
	@echo "  minikube start --cpus=4 --memory=8192"
	@echo "  kubectl create namespace mlops --dry-run=client -o yaml | kubectl apply -f -"
	@echo "  kubectl apply -f kserve/production-hardening.yaml"
	@echo "  kubectl apply -f kserve/inferenceservice.yaml"
	@echo "  kubectl apply -f kubernetes/training-and-monitoring-workloads.yaml"
	@echo "  kubectl apply -f monitoring/prometheus/prometheus.yml"

kubernetes-plan:
	@find kserve kubernetes monitoring -name '*.yaml' -maxdepth 3 -print

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

clean:
	rm -rf .local
