# Task 33 – Flask + PostgreSQL visit counter

```
app/   app.py, requirements.txt, Dockerfile
k8s/   00-namespace.yaml    flask-project namespace
       01-config.yaml       ConfigMap flask-db-config + Secret flask-db-secret
       02-postgres.yaml     Service + StatefulSet (PVC pgdata)
       03-db-init-job.yaml  creates the visits table (safe to re-run)
       04-flask.yaml        Deployment flask (2 replicas) + NodePort 30081
```

## Build & push
```bash
docker build -t berezovsky8/flask-visits:v2 app
docker push berezovsky8/flask-visits:v2
```

## Deploy
```bash
kubectl apply -f k8s/00-namespace.yaml -f k8s/01-config.yaml -f k8s/02-postgres.yaml
kubectl -n flask-project get pods,pvc            # postgres-0 Ready, PVC Bound

kubectl apply -f k8s/03-db-init-job.yaml
kubectl -n flask-project logs job/db-init        # CREATE TABLE

kubectl apply -f k8s/04-flask.yaml
```
Open `http://<node-ip>:30081`. On Docker Desktop, you can't reach the node IP from Windows, so use:
`kubectl -n flask-project port-forward svc/flask 5000:5000` → http://localhost:5000

## Recovery tests
```bash
kubectl -n flask-project delete pod <flask-pod>     # replaced, counter continues
kubectl -n flask-project delete pod postgres-0      # same PVC reattached, counter continues

# wrong ConfigMap: in 04-flask.yaml change configMapRef name to flask-db-config-wrong, then
kubectl apply -f k8s/04-flask.yaml
kubectl -n flask-project describe pod <new-pod>     # configmap "flask-db-config-wrong" not found
# change it back to flask-db-config, then
kubectl apply -f k8s/04-flask.yaml
kubectl -n flask-project rollout status deploy/flask
```
