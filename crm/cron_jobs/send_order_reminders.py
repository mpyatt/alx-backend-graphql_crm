#!/usr/bin/env python3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = Path("/tmp/order_reminders_log.txt")
ENDPOINT = "http://localhost:8000/graphql"

# Try several schema shapes so this works with your GraphQL no matter which filter style you kept.
QUERY_CANDIDATES = [
    # allOrders2 with filter input (our convenience wrapper)
    ("relay", gql("""
        query($since: DateTime!) {
          allOrders2(filter: { orderDateGte: $since }) {
            edges { node { id orderDate customer { email } } }
          }
        }
    """)),
    # allOrders with filter input (camel-cased)
    ("relay", gql("""
        query($since: DateTime!) {
          allOrders(filter: { orderDateGte: $since }) {
            edges { node { id orderDate customer { email } } }
          }
        }
    """)),
    # allOrders with django-filter arg style
    ("relay", gql("""
        query($since: DateTime!) {
          allOrders(orderDate_Gte: $since) {
            edges { node { id orderDate customer { email } } }
          }
        }
    """)),
    # plain list field
    ("plain", gql("""
        query($since: DateTime!) {
          orders(orderDateGte: $since) {
            id
            orderDate
            customer { email }
          }
        }
    """)),
]


def extract_orders(result, mode):
    if mode == "plain":
        return result.get("orders", []) or []
    # relay connection
    for key in ("allOrders2", "allOrders"):
        conn = result.get(key)
        if conn and "edges" in conn:
            return [e["node"] for e in conn["edges"] if e.get("node")]
    return []


def main():
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    transport = RequestsHTTPTransport(
        url=ENDPOINT, verify=False, retries=2, timeout=20)
    client = Client(transport=transport, fetch_schema_from_transport=False)

    orders = None
    last_err = None
    variables = {"since": since}

    for mode, query in QUERY_CANDIDATES:
        try:
            result = client.execute(query, variable_values=variables)
            orders = extract_orders(result, mode)
            break
        except Exception as e:
            last_err = e
            continue

    if orders is None:
        print(
            f"ERROR: GraphQL query attempts failed: {last_err}", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a") as f:
        for o in orders:
            oid = o.get("id")
            email = (o.get("customer") or {}).get("email")
            f.write(f"{ts} Reminder: order_id={oid} email={email}\n")

    print("Order reminders processed!")


if __name__ == "__main__":
    main()
