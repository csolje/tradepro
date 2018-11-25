from django.db import models
from django.contrib.auth.models import User
from pseparser.models import Company
from django.shortcuts import get_object_or_404

# Create your models here.
class Client(models.Model):
    user = models.OneToOneField(User)
    last_name = models.CharField(max_length=20)
    first_name = models.CharField(max_length=20)
    wallet = models.DecimalField(decimal_places=2, max_digits=20)
    watchlist = models.ManyToManyField(Company, related_name='watching', blank=True)
    agents = models.CharField(max_length=20, blank=True)
    LANGUAGE_CHOICES = (
        ('ja', 'Japanese'),
        ('en', 'English'),
    )
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='en',
        blank=True
    )
    def __str__(self):
        return str(self.last_name +', '+ self.first_name)

class Order(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    client = models.ForeignKey(Client)
    stock = models.ForeignKey(Company)
    METHOD_CHOICES = (
        ('B', 'Buy'),
        ('S', 'Sell'),
    )
    method = models.CharField(
        max_length=1,
        choices=METHOD_CHOICES,
        default='B',
    )
    ORDER_TYPE_CHOICES = (
        ('L', 'Limit Order'),
        ('O', 'Stop Order'),
        ('C', 'One Cancel Other Order')
    )
    order_type = models.CharField(
        max_length=1,
        choices=ORDER_TYPE_CHOICES,
        default='L',
    )
    EXECUTION_TYPE_CHOICES = (
        ('OP', 'Order Price'),
        ('MO', 'Market Order'),
        ('BP', 'Best Price'),
        ('LO', 'Limit Order'),
        ('WO', 'Width Order'),
        ('OC', 'One Cancel Other Order')
    )
    execution_type = models.CharField(
        max_length=2,
        choices=EXECUTION_TYPE_CHOICES,
        default='OP',
    )
    price = models.DecimalField(decimal_places=2, max_digits=20)
    upper_limit = models.DecimalField(decimal_places=2, max_digits=20)
    units = models.IntegerField()
    EXPIRATION_CHOICES = (
        ('C', 'Good Til Cancelled'),
        ('D', 'Good Til Date'),
    )
    expiration = models.CharField(
        max_length=1,
        choices=EXPIRATION_CHOICES,
        default='C',
    )
    STATUS_CHOICES = (
        ('Pen', 'Pending'),
        ('Par', 'Queued'),
        ('Inc', 'Partial'),
        ('Exe', 'Executed'),
        ('Rev', 'Processing'),
        ('Rej', 'Rejected'),
        ('Can', 'Cancelled'),
    )
    status = models.CharField(
        max_length=3,
        choices=STATUS_CHOICES,
        default='Pen',
    )
    charge = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    others = models.CharField(max_length=30, blank=True, null=True)


class Transaction(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    client = models.ForeignKey(Client)
    TRANSACTION_TYPE_CHOICES = (
        ('B', 'Buy'),
        ('S', 'Sell'),
        ('D', 'Dividend'),
        ('W', 'Withdrawal'),
        ('A', 'Add Fund'),
    )
    order_type = models.CharField(
        max_length=1,
        choices=TRANSACTION_TYPE_CHOICES,
        default='B',
    )
    note = models.CharField(max_length=30, blank=True, null=True)


class AdminNotification(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    client = models.ForeignKey(Client)
    order = models.IntegerField()
    message = models.CharField(max_length=30, blank=True, null=True)
    seen = models.IntegerField(default=0)

    def __str__(self):
        return str(self.message)

class Alert(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=30, blank=True, null=True)
    client = models.ForeignKey(Client)
    seen = models.IntegerField(default=0)

    def __str__(self):
        return str(self.message)

