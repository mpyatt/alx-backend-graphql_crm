from decimal import Decimal
from datetime import timedelta
from random import sample
from django.utils import timezone
from django.db import transaction

from crm.models import Customer, Product, Order

# --- Sample data (edit as you like) ---
CUSTOMERS = [
    {"name": "Alice Johnson",  "email": "alice@example.com", "phone": "+1234567890"},
    {"name": "Bob Smith",      "email": "bob@example.com",   "phone": "123-456-7890"},
    {"name": "Carol Baker",    "email": "carol@example.com", "phone": "+14445556666"},
    {"name": "Dave Wilson",    "email": "dave@example.com",  "phone": "+15105551234"},
    {"name": "Eve Cooper",     "email": "eve@example.com",   "phone": "555-000-1212"},
]

PRODUCTS = [
    {"name": "Laptop",     "price": Decimal("999.99"), "stock": 10},
    {"name": "Phone",      "price": Decimal("699.00"), "stock": 15},
    {"name": "Headphones", "price": Decimal("149.99"), "stock": 25},
    {"name": "Monitor",    "price": Decimal("229.00"), "stock": 8},
    {"name": "Keyboard",   "price": Decimal("89.50"),  "stock": 30},
]


def ensure_customers():
    out = []
    for row in CUSTOMERS:
        obj, _ = Customer.objects.get_or_create(
            email=row["email"],
            defaults={"name": row["name"], "phone": row["phone"]},
        )
        out.append(obj)
    return out


def ensure_products():
    out = []
    for row in PRODUCTS:
        obj, _ = Product.objects.get_or_create(
            name=row["name"],
            defaults={"price": row["price"], "stock": row["stock"]},
        )
        out.append(obj)
    return out


def create_orders(customers, products, num_orders=5, days_back=7):
    created = []
    for i in range(num_orders):
        customer = customers[i % len(customers)]
        picks = sample(products, k=min(len(products), max(1, (i % 3) + 1)))
        when = timezone.now() - timedelta(days=(i % days_back))
        with transaction.atomic():
            order = Order.objects.create(customer=customer, order_date=when)
            order.products.set(picks)
            total = sum((p.price for p in picks), Decimal("0"))
            order.total_amount = total
            order.save(update_fields=["total_amount"])
            created.append(order)
    return created


# -------- Run ----------
customers = ensure_customers()
products = ensure_products()

if not Order.objects.exists():
    create_orders(customers, products, num_orders=5)

print(
    f"Seed complete. Customers={Customer.objects.count()}, "
    f"Products={Product.objects.count()}, Orders={Order.objects.count()}"
)
