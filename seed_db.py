from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from crm.models import Customer, Product, Order


def get_or_create_customer(name, email, phone=""):
    obj, _ = Customer.objects.get_or_create(
        email=email,
        defaults={"name": name, "phone": phone},
    )
    return obj


def get_or_create_product(name, price, stock=0):
    obj, _ = Product.objects.get_or_create(
        name=name,
        defaults={"price": Decimal(str(price)), "stock": stock},
    )
    return obj


def ensure_order(customer, products, order_date=None):
    """
    Create an order for this customer for the given products if one with the
    same product set doesn't already exist today. Computes total_amount.
    """
    if order_date is None:
        order_date = timezone.now()

    # naive de-dup: look for any order today with exact same product ids
    today = order_date.date()
    existing = (
        Order.objects.filter(customer=customer, order_date__date=today)
        .prefetch_related("products")
    )
    product_ids = sorted([p.id for p in products])
    for o in existing:
        if sorted(list(o.products.values_list("id", flat=True))) == product_ids:
            return o  # already exists

    with transaction.atomic():
        order = Order.objects.create(customer=customer, order_date=order_date)
        order.products.set(products)
        total = Product.objects.filter(id__in=product_ids).aggregate_sum = (
            sum((p.price for p in products), Decimal("0"))
        )
        order.total_amount = total
        order.save(update_fields=["total_amount"])
        return order


def run():
    # ---- Customers
    alice = get_or_create_customer("Alice", "alice@example.com", "+1234567890")
    bob = get_or_create_customer("Bob",   "bob@example.com",   "123-456-7890")
    carol = get_or_create_customer("Carol", "carol@example.com")

    # ---- Products
    laptop = get_or_create_product("Laptop",   999.99, stock=10)
    mouse = get_or_create_product("Mouse",     24.99, stock=50)
    keyboard = get_or_create_product("Keyboard",  49.99, stock=40)
    monitor = get_or_create_product("Monitor",  199.99, stock=25)

    # ---- Orders
    ensure_order(alice, [laptop, mouse])
    ensure_order(bob,   [keyboard, mouse])
    ensure_order(carol, [monitor])

    print("✅ Seed complete:")
    print(f"  Customers: {Customer.objects.count()}")
    print(f"  Products : {Product.objects.count()}")
    print(f"  Orders   : {Order.objects.count()}")


if __name__ == "__main__":
    run()
