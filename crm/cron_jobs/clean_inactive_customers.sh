#!/bin/bash
# Deletes customers with no orders in the last 12 months and logs the count.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_FILE="/tmp/customer_cleanup_log.txt"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

COUNT=$(
  python "$REPO_DIR/manage.py" shell <<'PYCODE'
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from crm.models import Customer

cutoff = timezone.now() - timedelta(days=365)
qs = Customer.objects.annotate(
    recent=Count('orders', filter=Q(orders__order_date__gte=cutoff))
).filter(recent=0)

n = qs.count()
qs.delete()
print(n)
PYCODE
)

echo "$TIMESTAMP Deleted customers without orders in last year: $COUNT" >> "$LOG_FILE"
