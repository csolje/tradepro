from django.db import models


# Create your models here.

class Company(models.Model):
    symbol = models.CharField(unique=True, max_length=50)
    symbol_id = models.CharField(unique=True, max_length=20)
    company_id = models.CharField(max_length=20)
    security_name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now=True)
    security_status = models.CharField(max_length=20)
    listing_date = models.DateTimeField(null=True)
    security_type = models.CharField(max_length=20)
    subsector = models.CharField(max_length=20)

    foreign_limit = models.IntegerField(null=True)
    listed_shares = models.IntegerField(null=True)
    free_float_level = models.IntegerField(null=True)
    security_ISIN = models.CharField(max_length=50,null=True)
    par_value = models.IntegerField(null=True)
    board_lot = models.IntegerField(null=True)
    outstanding_shares = models.IntegerField(null=True)

    def __str__(self):
        return self.company_name

class OrderBook(models.Model):
    orderbook_id = models.IntegerField(null=True)
    company = models.ForeignKey(Company)
    price_decimal = models.IntegerField(null=True)

class StockPrice(models.Model):
    company = models.ForeignKey(Company)
    date_created = models.DateTimeField(auto_now=True)
    date_details = models.DateField(null=True)
    total_volume = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    percentage_change_close = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    last_traded_price = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    open_price = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    high_price = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    low_price = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    indicator = models.CharField(max_length=10, null=True)

    def __str__(self):
        return str(self.company.company_name)

class MarketOrder(models.Model):
    company = models.ForeignKey(Company)
    price = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    units = models.DecimalField(max_digits=20, decimal_places=5, null=True)
    date_reference = models.IntegerField(null=True)
    sequence_number = models.IntegerField(null=True)
    ORDERS_CHOICES = (
        ('b', 'Bid'),
        ('a', 'Ask'),
    )
    order_type = models.CharField(
        max_length=2,
        choices=ORDERS_CHOICES,
        default='en',
        blank=True
    )

    def __str__(self):
        return str(self.company.company_name +', '+ self.order_type)

class LastExecutedOrder(models.Model):
    company = models.ForeignKey(Company)
    price = models.DecimalField(decimal_places=5, max_digits=20, null=True)
    units = models.DecimalField(max_digits=20, decimal_places=5, null=True)
    passive_broker = models.IntegerField(null=True)
    active_broker = models.IntegerField(null=True)
    ORDERS_CHOICES = (
        ('b', 'Bid'),
        ('a', 'Ask'),
    )
    order_type = models.CharField(
        max_length=2,
        choices=ORDERS_CHOICES,
        default='en',
        blank=True
    )


class Broker(models.Model):
    broker = models.CharField(max_length=50)
    broker_id = models.IntegerField(null=True)

class Sector(models.Model):
    id_index = models.CharField(max_length=50)
    is_sectoral = models.BooleanField()
    sort_order = models.IntegerField()
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Subsector(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Index(models.Model):
    date_details = models.DateTimeField(null=True)
    security_symbol = models.CharField(unique=True, max_length=20)
    security_alias = models.CharField(max_length=255)
    japanese = models.CharField(max_length=255)
    percentage_change_close = models.DecimalField(decimal_places=2, max_digits=20)
    last_traded_price = models.DecimalField(decimal_places=2, max_digits=20)
    total_volume = models.DecimalField(decimal_places=2, max_digits=20)
    indicator = models.CharField(max_length=10)
    
    def __str__(self):
        return str(self.security_alias)

class SystemHealth(models.Model):
    name = models.CharField(max_length=50)
    timestamp = models.DateTimeField(null=True)

    def __str__(self):
        return str(self.name)

class SystemOption(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255)

    def __str__(self):
        return str(self.name)