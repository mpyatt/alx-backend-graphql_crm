import re
from decimal import Decimal
from typing import List, Tuple

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db import transaction, models
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter

PHONE_RE = re.compile(r"^\+?\d[\d\-]{6,}$")

# ---------- GraphQL Types (Relay) ----------


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        fields = ("id", "name", "email", "phone", "created_at")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        fields = ("id", "customer", "products", "total_amount", "order_date")


class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        pass  # no inputs

    ok = graphene.Boolean()
    message = graphene.String()
    products = graphene.List(ProductType)

    @staticmethod
    def mutate(root, info):
        low = list(Product.objects.filter(stock__lt=10).order_by("id"))
        for p in low:
            p.stock = (p.stock or 0) + 10
            p.save(update_fields=["stock"])
        return UpdateLowStockProducts(
            ok=True,
            message=f"Updated {len(low)} product(s).",
            products=low,
        )


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
    order_date = graphene.DateTime()  # optional


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


def to_pk(gid) -> str:
    return str(gid)


def fetch_nodes_or_errors(model, ids: List[str], label: str) -> Tuple[List[object], List[str]]:
    objs, errs = [], []
    for gid in ids:
        pk = to_pk(gid)
        try:
            objs.append(model.objects.get(pk=pk))
        except (ObjectDoesNotExist, ValueError):
            errs.append(f"Invalid {label} ID: {gid}")
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
            # compute total from DB with precision
            total = (
                Product.objects.filter(id__in=[p.id for p in products])
                .aggregate(sum=models.Sum("price"))["sum"] or Decimal("0")
            )
            order.total_amount = total
            order.save(update_fields=["total_amount"])

        return CreateOrderPayload(order=order)


# ---------- Filtering & Queries (Relay connections) ----------

class Query(graphene.ObjectType):
    hello = graphene.String()

    # Relay + django-filter (ordering provided via FilterSets' OrderingFilter)
    all_customers = DjangoFilterConnectionField(
        CustomerType, filterset_class=CustomerFilter)
    all_products = DjangoFilterConnectionField(
        ProductType,  filterset_class=ProductFilter)
    all_orders = DjangoFilterConnectionField(
        OrderType,    filterset_class=OrderFilter)

    def resolve_hello(root, info):
        return "Hello, GraphQL!"


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    update_low_stock_products = UpdateLowStockProducts.Field()
