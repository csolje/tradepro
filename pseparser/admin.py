from django.contrib import admin

# Register your models here.
from pseparser.models import Company, Sector, Subsector, Index, StockPrice, LastExecutedOrder, MarketOrder, OrderBook, Broker, SystemOption

class StockPricesAdmin(admin.ModelAdmin):
    list_display = ('company', 'date_details')


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'symbol','symbol_id')
    # inlines = [DetailInline, ]


class OrderBookAdmin(admin.ModelAdmin):
    list_display = ('orderbook_id', 'company','price_decimal')


class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation')


class BrokerAdmin(admin.ModelAdmin):
    list_display = ('broker', 'broker_id')



class SubsectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'sector_name')

    def sector_name(self, obj):
        if obj.sector is not None:
            return obj.sector.name
        else:
            return "n/a"
    sector_name.short_description = 'Sector'
    sector_name.admin_order_field = 'sector__name'

admin.site.register(Company, CompanyAdmin)
admin.site.register(OrderBook, OrderBookAdmin)
admin.site.register(StockPrice, StockPricesAdmin)
admin.site.register(LastExecutedOrder)
admin.site.register(Broker, BrokerAdmin)
admin.site.register(MarketOrder)
admin.site.register(Sector, SectorAdmin)
admin.site.register(Subsector, SubsectorAdmin)
admin.site.register(Index)
admin.site.register(SystemOption)
