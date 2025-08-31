import django_filters
from .models import Customer, Product, Order


class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains")
    email = django_filters.CharFilter(
        field_name="email", lookup_expr="icontains")
    created_at__gte = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte")
    created_at__lte = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte")
    phone_pattern = django_filters.CharFilter(method="filter_phone_pattern")
    order_by = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("name", "name"),
            ("email", "email"),
        )
    )

    def filter_phone_pattern(self, qs, name, value):
        return qs.filter(phone__startswith=value)

    class Meta:
        model = Customer
        fields = [
            "name", "email", "created_at__gte", "created_at__lte",
            "phone_pattern", "order_by"
        ]


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains")
    price__gte = django_filters.NumberFilter(
        field_name="price", lookup_expr="gte")
    price__lte = django_filters.NumberFilter(
        field_name="price", lookup_expr="lte")
    stock__gte = django_filters.NumberFilter(
        field_name="stock", lookup_expr="gte")
    stock__lte = django_filters.NumberFilter(
        field_name="stock", lookup_expr="lte")
    order_by = django_filters.OrderingFilter(
        fields=(
            ("stock", "stock"),
            ("price", "price"),
            ("name", "name"),
        )
    )

    class Meta:
        model = Product
        fields = ["name", "price__gte", "price__lte",
                  "stock__gte", "stock__lte", "order_by"]


class OrderFilter(django_filters.FilterSet):
    total_amount__gte = django_filters.NumberFilter(
        field_name="total_amount", lookup_expr="gte")
    total_amount__lte = django_filters.NumberFilter(
        field_name="total_amount", lookup_expr="lte")
    order_date__gte = django_filters.DateTimeFilter(
        field_name="order_date", lookup_expr="gte")
    order_date__lte = django_filters.DateTimeFilter(
        field_name="order_date", lookup_expr="lte")
    customer_name = django_filters.CharFilter(
        field_name="customer__name", lookup_expr="icontains")
    product_name = django_filters.CharFilter(
        field_name="products__name", lookup_expr="icontains")
    product_id = django_filters.NumberFilter(
        field_name="products__id", lookup_expr="exact")
    order_by = django_filters.OrderingFilter(
        fields=(
            ("order_date", "order_date"),
            ("total_amount", "total_amount"),
            ("customer__name", "customer_name"),
        )
    )

    class Meta:
        model = Order
        fields = [
            "total_amount__gte", "total_amount__lte",
            "order_date__gte", "order_date__lte",
            "customer_name", "product_name", "product_id",
            "order_by",
        ]
