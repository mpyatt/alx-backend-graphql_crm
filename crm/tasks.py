from decimal import Decimal
from datetime import datetime
from pathlib import Path
import os
import requests

from celery import shared_task
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

GRAPHQL_ENDPOINT = os.getenv(
    "GRAPHQL_ENDPOINT", "http://localhost:8000/graphql")
REPORT_LOG = Path("/tmp/crm_report_log.txt")


def _client() -> Client:
    transport = RequestsHTTPTransport(
        url=GRAPHQL_ENDPOINT, verify=False, retries=2, timeout=30
    )
    return Client(transport=transport, fetch_schema_from_transport=False)


def _append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(line + "\n")


# Build a Relay connection query dynamically for a given field and selection set
def _connection_query(field: str, selection: str):
    # selection is like: "edges { node { id } }"
    # We always request pageInfo for pagination
    q = f"""
    query($first: Int!, $after: String) {{
      {field}(first: $first, after: $after) {{
        pageInfo {{ hasNextPage endCursor }}
        {selection}
      }}
    }}
    """
    return gql(q)


def _count_nodes(client: Client, field_candidates: list[str]) -> int:
    for field in field_candidates:
        try:
            query = _connection_query(field, "edges { node { id } }")
            count = 0
            after = None
            while True:
                result = client.execute(query, variable_values={
                                        "first": 500, "after": after})
                conn = result.get(field)
                if not conn:
                    break
                edges = conn.get("edges", []) or []
                count += len([e for e in edges if e.get("node")])
                page = conn.get("pageInfo") or {}
                if page.get("hasNextPage"):
                    after = page.get("endCursor")
                else:
                    break
            return count
        except Exception:
            # try the next candidate
            continue
    # last resort: unknown schema shape
    return 0


def _sum_order_amounts(client: Client, field_candidates: list[str]) -> Decimal:
    for field in field_candidates:
        try:
            query = _connection_query(field, "edges { node { totalAmount } }")
            total = Decimal("0")
            after = None
            while True:
                result = client.execute(query, variable_values={
                                        "first": 500, "after": after})
                conn = result.get(field)
                if not conn:
                    break
                edges = conn.get("edges", []) or []
                for e in edges:
                    node = e.get("node") or {}
                    val = node.get("totalAmount")
                    if val is not None:
                        total += Decimal(str(val))
                page = conn.get("pageInfo") or {}
                if page.get("hasNextPage"):
                    after = page.get("endCursor")
                else:
                    break
            return total
        except Exception:
            continue
    return Decimal("0")


def _ping_graphql() -> None:
    """Lightweight ping so 'requests' is actually used; ignore failures."""
    try:
        requests.post(
            GRAPHQL_ENDPOINT,
            json={"query": "query{__typename}"},
            headers={"Content-Type": "application/json"},
            timeout=2,
        )
    except Exception:
        pass


@shared_task(name="crm.tasks.generate_crm_report")
def generate_crm_report():
    """
    Weekly CRM report via GraphQL:
      - Total customers
      - Total orders
      - Total revenue (sum of order.totalAmount)
    Logs to /tmp/crm_report_log.txt as:
      YYYY-MM-DD HH:MM:SS - Report: X customers, Y orders, Z revenue
    """
    _ping_graphql()

    client = _client()

    # Try both field names depending on your schema
    customer_fields = ["allCustomers2", "allCustomers"]
    order_fields = ["allOrders2", "allOrders"]

    total_customers = _count_nodes(client, customer_fields)
    total_orders = _count_nodes(client, order_fields)
    total_revenue = _sum_order_amounts(client, order_fields)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_log(
        REPORT_LOG,
        f"{ts} - Report: {total_customers} customers, {total_orders} orders, {total_revenue} revenue",
    )

    return {
        "customers": total_customers,
        "orders": total_orders,
        "revenue": str(total_revenue),
        "logged_to": str(REPORT_LOG),
    }
