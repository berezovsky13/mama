# Task 33 – Flask + PostgreSQL visit counter

Every visit to the home page is saved in PostgreSQL. The page shows the total count
and the name of the Pod (or machine/container) that served it.

```
app/   app.py, requirements.txt, Dockerfile
k8s/   00-namespace.yaml    flask-project namespace
       01-config.yaml       ConfigMap flask-db-config + Secret flask-db-secret
       02-postgres.yaml     Service + StatefulSet (PVC pgdata)
       03-db-init-job.yaml  creates the visits table (safe to re-run)
       04-flask.yaml        Deployment flask (2 replicas) + NodePort 30081
```

All commands below run in **PowerShell** from the `Task33` folder unless noted.

---

## Step 1 – Run the code from the CLI

The app needs a PostgreSQL database. Start one in Docker:

```powershell
docker run -d --name postgres -e POSTGRES_DB=visitsdb -e POSTGRES_USER=labuser -e POSTGRES_PASSWORD=labpassword123 -p 5432:5432 -v pgdata:/var/lib/postgresql/data postgres:16
```

Wait a few seconds, then create the `visits` table:

```powershell
docker exec postgres psql -U labuser -d visitsdb -c "CREATE TABLE IF NOT EXISTS visits (id SERIAL PRIMARY KEY, visited_at TIMESTAMP DEFAULT now());"
```

Create a virtual environment and install the packages (first time only):

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r app\requirements.txt
```

Set the database settings (only last in the current terminal) and run the app:

```powershell
$env:DB_HOST="localhost"; $env:DB_PORT="5432"; $env:DB_NAME="visitsdb"; $env:DB_USER="labuser"; $env:DB_PASSWORD="labpassword123"
.venv\Scripts\python app\app.py
```

Open http://localhost:5000 and refresh – the counter goes up.
Stop the app with `Ctrl+C` (keep the `postgres` container running for step 2).

---

## Step 2 – Run it as a container

Build the image:

```powershell
docker build -t berezovsky8/flask-visits:v2 app
```

Create a network so the Flask container can reach the database by the name `postgres`
(the default Docker network has no name lookup between containers):

```powershell
docker network create task33-net
docker network connect task33-net postgres
```

Run the Flask container (`DB_HOST=postgres`, because inside a container `localhost` is the container itself):

```powershell
docker run -d --name flask --network task33-net -p 5000:5000 -e DB_HOST=postgres -e DB_PORT=5432 -e DB_NAME=visitsdb -e DB_USER=labuser -e DB_PASSWORD=labpassword123 berezovsky8/flask-visits:v2
```

Open http://localhost:5000 – the count continues from step 1.
`docker logs flask` shows the app output.

Push the image to Docker Hub (Kubernetes pulls it from there):

```powershell
docker push berezovsky8/flask-visits:v2
```

Clean up before moving to Kubernetes:

```powershell
docker rm -f flask postgres
docker network rm task33-net
docker volume rm pgdata
```

---

## Step 3 – Deploy PostgreSQL on Kubernetes

```powershell
kubectl apply -f k8s/00-namespace.yaml -f k8s/01-config.yaml -f k8s/02-postgres.yaml
kubectl -n flask-project get pods,pvc        # postgres-0 1/1 Running, PVC Bound
```

## Step 4 – Initialize the database

```powershell
kubectl apply -f k8s/03-db-init-job.yaml
kubectl -n flask-project get job db-init     # Complete
kubectl -n flask-project logs job/db-init    # CREATE TABLE
```

Safe to run again – `IF NOT EXISTS` keeps existing visits:

```powershell
kubectl -n flask-project delete job db-init
kubectl apply -f k8s/03-db-init-job.yaml
```

## Step 5 – Deploy Flask and open it

```powershell
kubectl apply -f k8s/04-flask.yaml
kubectl -n flask-project get pods,svc
kubectl get nodes -o wide                    # node INTERNAL-IP
```

Open `http://<node-ip>:30081` and refresh – the counter goes up and the Pod name changes between the 2 replicas.

On Docker Desktop you can't reach the node IP from Windows, so forward the port instead:

```powershell
kubectl -n flask-project port-forward svc/flask 30081:5000
```

and open http://localhost:30081 (a port-forward always uses one Pod).

## Step 6 – Recovery tests

Delete a Flask Pod – the Deployment replaces it and the count continues:

```powershell
kubectl -n flask-project get pods
kubectl -n flask-project delete pod <flask-pod-name>
kubectl -n flask-project rollout status deploy/flask
```

Delete the PostgreSQL Pod – the StatefulSet recreates `postgres-0` with the same PVC and the count continues:

```powershell
kubectl -n flask-project delete pod postgres-0
kubectl -n flask-project get pods,pvc
```

Wrong ConfigMap reference – in `k8s/04-flask.yaml` change `name: flask-db-config` under `configMapRef` to `flask-db-config-wrong`, then:

```powershell
kubectl apply -f k8s/04-flask.yaml
kubectl -n flask-project get pods                     # new Pod: CreateContainerConfigError
kubectl -n flask-project describe pod <new-pod-name>  # configmap "flask-db-config-wrong" not found
```

Change it back to `flask-db-config` and apply again:

```powershell
kubectl apply -f k8s/04-flask.yaml
kubectl -n flask-project rollout status deploy/flask
```
