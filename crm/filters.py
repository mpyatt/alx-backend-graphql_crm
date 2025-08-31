import django_filters as filters
from .models import Customer, Product, Order


class CustomerFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")
    created_at__gte = filters.DateFilter(
        field_name="created_at", lookup_expr="gte")
    created_at__lte = filters.DateFilter(
        field_name="created_at", lookup_expr="lte")
    # Challenge: phone pattern (starts with +1, as example)
    phone_pattern = filters.CharFilter(method="filter_phone_pattern")

    def filter_phone_pattern(self, qs, name, value):
        return qs.filter(phone__startswith=value)

    class Meta:
        model = Customer
        fields = ["name", "email", "created_at__gte",
                  "created_at__lte", "phone_pattern"]


class ProductFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    price__gte = filters.NumberFilter(field_name="price", lookup_expr="gte")
    price__lte = filters.NumberFilter(field_name="price", lookup_expr="lte")
    stock__gte = filters.NumberFilter(field_name="stock", lookup_expr="gte")
    stock__lte = filters.NumberFilter(field_name="stock", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["name", "price__gte",
                  "price__lte", "stock__gte", "stock__lte"]


class OrderFilter(filters.FilterSet):
    total_amount__gte = filters.NumberFilter(
        field_name="total_amount", lookup_expr="gte")
    total_amount__lte = filters.NumberFilter(
        field_name="total_amount", lookup_expr="lte")
    order_date__gte = filters.DateTimeFilter(
        field_name="order_date", lookup_expr="gte")
    order_date__lte = filters.DateTimeFilter(
        field_name="order_date", lookup_expr="lte")
    customer_name = filters.CharFilter(
        field_name="customer__name", lookup_expr="icontains")
    product_name = filters.CharFilter(
        field_name="products__name", lookup_expr="icontains")
    product_id = filters.NumberFilter(
        field_name="products__id", lookup_expr="exact")

    class Meta:
        model = Order
        fields = [
            "total_amount__gte", "total_amount__lte",
            "order_date__gte", "order_date__lte",
            "customer_name", "product_name", "product_id"
        ]
