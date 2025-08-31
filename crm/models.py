from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.name} <{self.email}>"


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self): return f"{self.name}"


class Order(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="orders")
    products = models.ManyToManyField(Product, related_name="orders")
    total_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0)
    order_date = models.DateTimeField(auto_now_add=True)
