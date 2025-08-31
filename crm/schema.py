import re
from decimal import Decimal
from typing import List, Tuple, Optional

import graphene
from graphene_django import DjangoObjectType
from django.db import transaction, models
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from .models import Customer, Product, Order

PHONE_RE = re.compile(r"^\+?\d[\d\-]{6,}$")

# ---------- GraphQL Types (no Relay) ----------


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone", "created_at")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")

# ---------- Inputs ----------


class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class CreateCustomerInput(CustomerInput):
    pass


class BulkCustomerInput(CustomerInput):
    pass


class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(default_value=0)


class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
    order_date = graphene.DateTime()

# ---------- Payloads ----------


class CreateCustomerPayload(graphene.ObjectType):
    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)


class BulkCreateCustomersPayload(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)


class CreateProductPayload(graphene.ObjectType):
    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)


class CreateOrderPayload(graphene.ObjectType):
    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

# ---------- Helpers ----------


def validate_new_customer(data: CustomerInput) -> List[str]:
    errors = []
    if not PHONE_RE.match(data.phone) if data.phone else False:
        errors.append("Invalid phone format.")
    if Customer.objects.filter(email=data.email).exists():
        errors.append("Email already exists.")
    return errors


def fetch_nodes_or_errors(model, ids: List[str], label: str) -> Tuple[List[object], List[str]]:
    objs, errs = [], []
    for pk in ids:
        try:
            objs.append(model.objects.get(pk=pk))
        except (ObjectDoesNotExist, ValueError):
            errs.append(f"Invalid {label} ID: {pk}")
    return objs, errs

# ---------- Mutations ----------


class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    Output = CreateCustomerPayload

    @staticmethod
    def mutate(root, info, input: CreateCustomerInput):
        errs = validate_new_customer(input)
        if errs:
            return CreateCustomerPayload(errors=errs, message="Validation failed")
        cust = Customer(name=input.name, email=input.email,
                        phone=input.phone or "")
        cust.save()
        return CreateCustomerPayload(customer=cust, message="Customer created")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(BulkCustomerInput, required=True)

    Output = BulkCreateCustomersPayload

    @staticmethod
    def mutate(root, info, input):
        created, errors = [], []
        with transaction.atomic():
            for idx, rec in enumerate(input):
                errs = validate_new_customer(rec)
                if errs:
                    errors.append(f"Row {idx+1}: " + "; ".join(errs))
                    continue
                cust = Customer(name=rec.name, email=rec.email,
                                phone=rec.phone or "")
                try:
                    cust.full_clean()
                    cust.save()
                    created.append(cust)
                except ValidationError as e:
                    errors.append(f"Row {idx+1}: {e}")
        return BulkCreateCustomersPayload(customers=created, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    Output = CreateProductPayload

    @staticmethod
    def mutate(root, info, input: CreateProductInput):
        errs = []
        try:
            price = Decimal(str(input.price))
            if price <= 0:
                errs.append("Price must be positive.")
        except Exception:
            errs.append("Invalid price.")
        if input.stock is not None and input.stock < 0:
            errs.append("Stock cannot be negative.")
        if errs:
            return CreateProductPayload(errors=errs)

        p = Product(name=input.name, price=price, stock=input.stock or 0)
        p.save()
        return CreateProductPayload(product=p)


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    Output = CreateOrderPayload

    @staticmethod
    def mutate(root, info, input: CreateOrderInput):
        # Customer
        customers, errs = fetch_nodes_or_errors(
            Customer, [input.customer_id], "customer")
        if errs:
            return CreateOrderPayload(errors=errs)
        customer = customers[0]

        # Products
        products, perrs = fetch_nodes_or_errors(
            Product, input.product_ids, "product")
        if perrs:
            return CreateOrderPayload(errors=perrs)
        if not products:
            return CreateOrderPayload(errors=["At least one product must be provided."])

        with transaction.atomic():
            order = Order(customer=customer)
            if input.order_date:
                order.order_date = input.order_date
            order.save()
            order.products.set(products)
            total = (
                Product.objects.filter(id__in=[p.id for p in products])
                .aggregate(sum=models.Sum("price"))["sum"] or Decimal("0")
            )
            order.total_amount = total
            order.save(update_fields=["total_amount"])

        return CreateOrderPayload(order=order)

# ---------- Query (plain lists + explicit filters) ----------


class Query(graphene.ObjectType):
    hello = graphene.String()

    # Customers
    all_customers = graphene.List(
        CustomerType,
        name_icontains=graphene.String(),
        email_icontains=graphene.String(),
        created_at_gte=graphene.Date(),
        created_at_lte=graphene.Date(),
        phone_pattern=graphene.String(),          # e.g., "+1"
        # e.g., ["-created_at", "name"]
        order_by=graphene.List(graphene.String),
    )

    # Products
    all_products = graphene.List(
        ProductType,
        name_icontains=graphene.String(),
        price_gte=graphene.Decimal(),
        price_lte=graphene.Decimal(),
        stock_gte=graphene.Int(),
        stock_lte=graphene.Int(),
        order_by=graphene.List(graphene.String),  # e.g., ["-stock"]
    )

    # Orders
    all_orders = graphene.List(
        OrderType,
        total_amount_gte=graphene.Decimal(),
        total_amount_lte=graphene.Decimal(),
        order_date_gte=graphene.DateTime(),
        order_date_lte=graphene.DateTime(),
        customer_name=graphene.String(),
        product_name=graphene.String(),
        product_id=graphene.ID(),
        order_by=graphene.List(graphene.String),  # e.g., ["-order_date"]
    )

    def resolve_hello(root, info):
        return "Hello, GraphQL!"

    # --- Resolvers ---
    def resolve_all_customers(root, info, **kwargs):
        qs = Customer.objects.all()
        if (v := kwargs.get("name_icontains")):
            qs = qs.filter(name__icontains=v)
        if (v := kwargs.get("email_icontains")):
            qs = qs.filter(email__icontains=v)
        if (v := kwargs.get("created_at_gte")):
            qs = qs.filter(created_at__date__gte=v)
        if (v := kwargs.get("created_at_lte")):
            qs = qs.filter(created_at__date__lte=v)
        if (v := kwargs.get("phone_pattern")):
            qs = qs.filter(phone__startswith=v)
        if (ob := kwargs.get("order_by")):
            qs = qs.order_by(*ob)
        return qs

    def resolve_all_products(root, info, **kwargs):
        qs = Product.objects.all()
        if (v := kwargs.get("name_icontains")):
            qs = qs.filter(name__icontains=v)
        if (v := kwargs.get("price_gte")):
            qs = qs.filter(price__gte=v)
        if (v := kwargs.get("price_lte")):
            qs = qs.filter(price__lte=v)
        if (v := kwargs.get("stock_gte")):
            qs = qs.filter(stock__gte=v)
        if (v := kwargs.get("stock_lte")):
            qs = qs.filter(stock__lte=v)
        if (ob := kwargs.get("order_by")):
            qs = qs.order_by(*ob)
        return qs

    def resolve_all_orders(root, info, **kwargs):
        qs = Order.objects.select_related(
            "customer").prefetch_related("products")
        if (v := kwargs.get("total_amount_gte")):
            qs = qs.filter(total_amount__gte=v)
        if (v := kwargs.get("total_amount_lte")):
            qs = qs.filter(total_amount__lte=v)
        if (v := kwargs.get("order_date_gte")):
            qs = qs.filter(order_date__gte=v)
        if (v := kwargs.get("order_date_lte")):
            qs = qs.filter(order_date__lte=v)
        if (v := kwargs.get("customer_name")):
            qs = qs.filter(customer__name__icontains=v)
        if (v := kwargs.get("product_name")):
            qs = qs.filter(products__name__icontains=v)
        if (v := kwargs.get("product_id")):
            qs = qs.filter(products__id=v)
        if (ob := kwargs.get("order_by")):
            qs = qs.order_by(*ob)
        return qs


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
