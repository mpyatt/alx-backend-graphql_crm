from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.db.models import Count, Q
from django.utils import timezone as dj_tz

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from .models import Customer, Product

# ===== Config: logs + GraphQL =====
HEARTBEAT_LOG = Path("/tmp/crm_heartbeat_log.txt")
LOW_STOCK_LOG = Path("/tmp/low_stock_updates_log.txt")
CLEANUP_LOG = Path("/tmp/customer_cleanup_log.txt")
REMINDERS_LOG = Path("/tmp/order_reminders_log.txt")
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"


def _append_log(path: Path, line: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(line + "\n")


def _client() -> Client:
    transport = RequestsHTTPTransport(
        url=GRAPHQL_ENDPOINT, verify=False, retries=2, timeout=20)
    return Client(transport=transport, fetch_schema_from_transport=False)

# ===== A) Customer Cleanup (weekly) =====


def customer_cleanup():
    cutoff = dj_tz.now() - timedelta(days=365)
    qs = Customer.objects.annotate(
        recent=Count("orders", filter=Q(orders__order_date__gte=cutoff))
    ).filter(recent=0)
    n = qs.count()
    qs.delete()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_log(
        CLEANUP_LOG, f"{ts} Deleted customers without orders in last year: {n}")


# ===== B) Order Reminders (daily) =====
_QUERY_CANDIDATES = [
    gql("""query($since: DateTime!) {
      allOrders2(filter: { orderDateGte: $since }) { edges { node { id orderDate customer { email } } } }
    }"""),
    gql("""query($since: DateTime!) {
      allOrders(filter: { orderDateGte: $since }) { edges { node { id orderDate customer { email } } } }
    }"""),
    gql("""query($since: DateTime!) {
      allOrders(orderDate_Gte: $since) { edges { node { id orderDate customer { email } } } }
    }"""),
]


def _extract_orders(result):
    for key in ("allOrders2", "allOrders"):
        conn = result.get(key)
        if conn and "edges" in conn:
            return [e["node"] for e in conn["edges"] if e.get("node")]
    return []


def send_order_reminders():
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    client = _client()
    orders, last_err = [], None
    for q in _QUERY_CANDIDATES:
        try:
            result = client.execute(q, variable_values={"since": since})
            orders = _extract_orders(result)
            break
        except Exception as e:
            last_err = e
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not orders and last_err:
        _append_log(REMINDERS_LOG, f"{ts} ERROR querying GraphQL: {last_err}")
    else:
        for o in orders:
            oid = o.get("id")
            email = (o.get("customer") or {}).get("email")
            _append_log(REMINDERS_LOG,
                        f"{ts} Reminder: order_id={oid} email={email}")
    print("Order reminders processed!")

# ===== C) Heartbeat (every 5 minutes) =====


def log_crm_heartbeat():
    """
    Append a heartbeat in the exact format:
    DD/MM/YYYY-HH:MM:SS CRM is alive
    """
    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    _append_log(HEARTBEAT_LOG, f"{ts} CRM is alive")
    try:
        client = _client()
        client.execute(gql("query { hello }"))
    except Exception:
        pass

# ===== D) Low-stock updater (every 12 hours) =====


def update_low_stock():
    """
    Requires UpdateLowStockProducts registered in crm/schema.py:
      update_low_stock_products = UpdateLowStockProducts.Field()
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        client = _client()
        mutation = gql("""
          mutation {
            updateLowStockProducts {
              ok
              message
              products { id name stock }
            }
          }
        """)
        result = client.execute(mutation)
        payload = result.get("updateLowStockProducts", {}) or {}
        products = payload.get("products", []) or []
        for p in products:
            _append_log(LOW_STOCK_LOG,
                        f"{ts} Updated '{p['name']}' -> stock={p['stock']}")
    except Exception as e:
        _append_log(LOW_STOCK_LOG, f"{ts} ERROR: {e}")
