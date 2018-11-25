from django.contrib import admin
from .models import *
from .forms import *

# Register your models here.

from django.contrib import admin
class OrderAdmin(admin.ModelAdmin):
    #form = OrderAdminForm
    model = Order
    fields = ('status', 'client', 'stock', 'method', 'order_type', 'charge', 'execution_type', 'price', 'upper_limit', 'units', 'expiration', 'others')


class AlertAdmin(admin.ModelAdmin):
    list_display = ('client', 'message')

class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('client', 'order', 'message')


admin.site.register(Client)
admin.site.register(Order, OrderAdmin)
admin.site.register(Transaction)
admin.site.register(Alert, AlertAdmin)
admin.site.register(AdminNotification, AdminNotificationAdmin)
