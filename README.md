# airflow-setup

Apache Airflow 3 on Kubernetes with the official Helm chart, set up the way
you'd run it for a team: tasks in their own pods, DAGs deployed by merging to
`main`, task logs in S3, an external PostgreSQL behind PgBouncer, and no
secrets in the values file. Two example DAGs show the patterns the setup is
meant for, and CI loads them with a real Airflow install before they reach the
cluster.

## Layout

```
helm/values.yaml          production-style values (chart 1.22.0, Airflow 3.2.2)
helm/values-local.yaml    self-contained values for kind or minikube
scripts/create-secrets.sh database URI and the keys that must survive upgrades
scripts/install.sh        helm upgrade --install with the pinned chart version
dags/orders_daily.py      S3 export -> revenue per region -> PostgreSQL
dags/revenue_report.py    runs whenever daily_revenue is updated
dags/orders_lib/          plain-Python logic the DAGs call, unit-tested
sql/daily_revenue.sql     target table
tests/                    unit tests and DAG integrity tests
```

## Deploying

```bash
METADATA_DB_URI='postgresql://airflow:...@db.example.com:5432/airflow' scripts/create-secrets.sh
scripts/install.sh
```

Before installing, set your repository URL under `dags.gitSync.repo`, the S3
log location under `config.logging`, the IAM role ARN on the service accounts
and the ingress host.

For a laptop cluster with the bundled PostgreSQL and an `admin`/`admin` user:

```bash
VALUES=helm/values-local.yaml scripts/install.sh
kubectl -n airflow port-forward svc/airflow-api-server 8080:8080
```

## Design choices

| Choice | Why |
|--------|-----|
| KubernetesExecutor | One pod per task: no idle Celery workers, per-task resources, and a task that leaks memory only takes itself down |
| External PostgreSQL + PgBouncer | The metadata DB outlives the cluster and gets managed backups; every task pod opens connections, so they're pooled |
| Keys in pre-created secrets | Left to the chart, the Fernet, API, JWT and webserver keys are regenerated on upgrade, which breaks stored connections and logs everyone out |
| git-sync for DAGs | Merging to `main` is the deploy; no image rebuild for a DAG change |
| Task logs in S3 via IRSA | Task pods are deleted when they finish; the UI reads logs back from S3. No static AWS keys |
| Two schedulers and API servers, with PDBs | Node drains and upgrades don't stop scheduling or the UI |
| Weekly metadata cleanup | `airflow db clean` keeps 30 days of history so the database doesn't grow without bound |
| No default admin user | Users come from SSO or `airflow users create` |

## The example DAGs

**orders_daily** runs at midnight UTC. It reads `orders/<date>.csv` from the
bucket in the `orders_bucket` Variable, keeps completed orders, rejects
duplicates and bad amounts, and writes revenue per region to `daily_revenue`.
It deletes the day's rows before inserting, so retries and re-runs never
double count. Its `load` task declares the `daily_revenue` asset as an outlet.

**revenue_report** has no clock schedule: it's scheduled on that asset, so it
runs as soon as `orders_daily` finishes loading, builds a 7-day Markdown
report and writes it to the `reports_bucket`.

Both follow the same habits: business logic lives in `orders_lib/` as plain
functions; provider imports happen inside tasks, which keeps DAG parsing fast;
large data moves through S3 and PostgreSQL, not XCom; and `catchup` is off so
a deploy never triggers a surprise backfill.

Connections they expect: `aws_default` (left empty to use the pod's IAM role)
and `analytics` (PostgreSQL). Variables: `orders_bucket` and `reports_bucket`.

## Tests

```bash
pip install "apache-airflow==3.2.2" pytest \
  --constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.2.2/constraints-3.12.txt
AIRFLOW__CORE__LOAD_EXAMPLES=False pytest
```

- **Unit tests** cover the transform and the report formatting.
- **DAG integrity tests** load `dags/` through Airflow's `DagBag`, as the DAG
  processor does, and fail on any import error. They also check DAG IDs,
  dependencies, retries, the asset wiring and that no DAG has catchup
  enabled.

These tests caught a real bug during development: `revenue_report`
originally imported the asset from `orders_daily.py`, which defined the
`orders_daily` DAG a second time.

CI also renders the chart with both values files and validates the output
with kubeconform, and runs shellcheck on the scripts.
