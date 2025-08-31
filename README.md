# alx-backend-graphql_crm

A Django + GraphQL CRM backend for ALX ProDev Backend Engineering tasks.

## ✨ Features

- **GraphQL API** powered by `graphene-django` (`/graphql` with GraphiQL UI)
- **Models**: `Customer`, `Product`, `Order`
- **Mutations**: create customer(s), product, and orders (with validation & totals)
- **Filtering** with `django-filter` (customers/products/orders w/ ranges & icontains)
- **Cron jobs** (via `django-crontab`):
  - Heartbeat every 5 minutes → `tmp/crm_heartbeat_log.txt`
  - Low-stock updater every 12 hours (GraphQL mutation) → `tmp/low_stock_updates_log.txt`
- **System cron helpers**:
  - Weekly customer cleanup (Sun 2:00) → `tmp/customer_cleanup_log.txt`
  - Daily order reminders (08:00) via GraphQL → `tmp/order_reminders_log.txt`
- **Celery + Beat** (optional): weekly CRM report → `tmp/crm_report_log.txt`
- **Docker Compose** stack: Postgres, Redis, Django server, Celery worker/beat, cron sidecar
- **One-liner seeding** with `seed_db.py` (or auto-seed on container start)

---

## 🚀 Quick Start (Docker)

```bash
git clone https://github.com/mpyatt/alx-backend-graphql_crm.git
cd alx-backend-graphql_crm

# Start all services (Postgres, Redis, server, worker, beat, cron)
docker compose up --build
````

Now open: [http://localhost:8000/graphql](http://localhost:8000/graphql)

> By default the server container seeds 5 customers, 5 products, and 5 recent orders on first boot.

### Environment knobs (Compose)

The server service respects these env vars (set in `compose.yml` or `.env`):

- `DJANGO_MIGRATE=1` — run migrations on start (others set to `0`)
- `DB_SEED=1` — run `seed_db.py` once on start (set to `0` to skip)
- `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,server`
- `POSTGRES_HOST=postgres`, plus `POSTGRES_DB/USER/PASSWORD/PORT`
- `CELERY_BROKER_URL=redis://redis:6379/0`, `CELERY_RESULT_BACKEND=redis://redis:6379/0`

Logs from cron/Celery land in **`./tmp/`** (project-relative).

---

## 🧑‍💻 Local Development (without Docker)

Requirements:

- Python 3.10+
- Postgres 14+ running locally (or adjust `DATABASES` in settings)
- Redis (if you want Celery/Beat locally)

Setup:

```bash
git clone https://github.com/mpyatt/alx-backend-graphql_crm.git
cd alx-backend-graphql_crm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ensure DB env matches your Postgres
export POSTGRES_HOST=localhost
export POSTGRES_DB=crm
export POSTGRES_USER=crm
export POSTGRES_PASSWORD=crm

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

(Optionally seed)

```bash
python manage.py shell < seed_db.py
```

---

## 🔌 GraphQL Usage

Open [http://localhost:8000/graphql](http://localhost:8000/graphql) and run:

```graphql
{
  hello
}
```

### Example Mutations

> **Note on decimals**: when sending JSON to `/graphql`, send decimals as **strings** (e.g., `"999.99"`) to satisfy the `Decimal` scalar.

Create a customer:

```graphql
mutation {
  createCustomer(input: {
    name: "Alice",
    email: "alice@example.com",
    phone: "+1234567890"
  }) {
    customer { id name email phone }
    message
    errors
  }
}
```

Bulk create customers:

```graphql
mutation {
  bulkCreateCustomers(input: [
    { name: "Bob", email: "bob@example.com", phone: "123-456-7890" },
    { name: "Carol", email: "carol@example.com" }
  ]) {
    customers { id name email }
    errors
  }
}
```

Create a product:

```graphql
mutation {
  createProduct(input: {
    name: "Laptop",
    price: "999.99",
    stock: 10
  }) {
    product { id name price stock }
    errors
  }
}
```

Create an order:

```graphql
mutation {
  createOrder(input: {
    customerId: "1",
    productIds: ["1", "2"]
  }) {
    order {
      id
      customer { name }
      products { name price }
      totalAmount
      orderDate
    }
    errors
  }
}
```

### Filtering (Relay connections)

Customers (name icontains + createdAt ≥ 2025-01-01):

```graphql
query {
  allCustomers(name: "Ali", createdAt_Gte: "2025-01-01") {
    edges { node { id name email createdAt } }
  }
}
```

Products by price range, sorted by stock desc:

```graphql
query {
  allProducts(price_Gte: 100, price_Lte: 1000, orderBy: "-stock") {
    edges {
      node {
        id
        name
        price
        stock
      }
    }
  }
}
```

Orders by customer/product name & total:

```graphql
query {
  allOrders(customerName: "Alice", productName: "Laptop", totalAmount_Gte: 500) {
    edges {
      node {
        id
        customer {
          name
        }
        products {
          edges {
            node {
              name
            }
          }
        }
        totalAmount
        orderDate
      }
    }
  }
}
```

---

## ⏱️ Scheduled Jobs

### django-crontab (inside app)

Configured in `settings.py`:

- Heartbeat every 5m → `crm.cron.log_crm_heartbeat` → `tmp/crm_heartbeat_log.txt`
- Low-stock every 12h → `crm.cron.update_low_stock` → `tmp/low_stock_updates_log.txt`

Install/show (Compose cron service does this automatically):

```bash
docker compose exec cron python manage.py crontab show
```

### System cron helpers (files in `crm/cron_jobs/`)

- `clean_inactive_customers.sh` (Sun 02:00)
- `send_order_reminders.py` (daily 08:00 via GraphQL)

Example crontab lines:

```sh
0 2 * * 0 /bin/bash alx-backend-graphql_crm/crm/cron_jobs/clean_inactive_customers.sh
0 8 * * * /bin/bash alx-backend-graphql_crm/crm/cron_jobs/send_order_reminders.py
```

---

## 🐇 Celery & Celery Beat (optional)

- Task: `crm.tasks.generate_crm_report`
- Beat schedule: Mondays 06:00 (configurable in `settings.py`)
- Output: `tmp/crm_report_log.txt`

Trigger manually:

```bash
docker compose exec server python manage.py shell -c "from crm.tasks import generate_crm_report; generate_crm_report.delay()"
```

---

## 📁 Project Structure (key files)

```text
alx-backend-graphql_crm/
├─ alx_backend_graphql_crm/        # Project settings / urls
│  ├─ settings.py
│  └─ urls.py
├─ crm/                            # CRM app
│  ├─ models.py
│  ├─ schema.py                    # GraphQL schema (queries + mutations)
│  ├─ filters.py                   # django-filter FilterSets
│  ├─ cron.py                      # heartbeat/cleanup/reminders/low-stock
│  ├─ tasks.py                     # Celery task for weekly report
│  ├─ celery.py                    # Celery app init
│  ├─ cron_jobs/
│  │  ├─ clean_inactive_customers.sh
│  │  └─ send_order_reminders.py
│  └─ README.md                    # Celery & ops notes
├─ graphql_crm/
│  └─ schema.py                    # Project-level schema glue
├─ seed_db.py                      # Simple seeding script
├─ entrypoint.sh                   # Wait, migrate (optional), seed, etc.
├─ compose.yml
├─ Dockerfile
├─ requirements.txt
├─ manage.py
├─ tmp/                            # Logs from cron/tasks (git-ignored)
├─ .gitignore
└─ README.md
```

---

## 🧰 Troubleshooting

- **400 at `/graphql`** using `curl`: send a query body.

  ```bash
  curl -s -X POST -H "Content-Type: application/json" \
    -d '{"query":"{ hello }"}' http://localhost:8000/graphql
  ```

- **`DisallowedHost`**: set `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,server` (Compose already does).
- **Cron permission error**: cron service runs as root in Compose (`user: "0:0"`).
- **Logs**: all job logs are relative to the repo in `./tmp/*_log.txt`.
