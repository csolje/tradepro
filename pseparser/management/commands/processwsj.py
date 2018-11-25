import os
import requests
import datetime
from django.core.management.base import LabelCommand, BaseCommand

from pseparser.models import Company, StockPrice
from roi import settings

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('symbols')
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all', 
            default=False,
            help='Process all companies',
        )


    def handle(self, *args, **options):
        list_symbols = []
        if options['all']:
            companies = list(Company.objects.all())
            for company in companies:
                list_symbols.append(company.symbol)
        else:
            list_symbols.extend(options['symbols'].split(','))

        for symbol in list_symbols:

            company = Company.objects.filter(symbol=symbol).first()

            print("processing: " + symbol)
            filename = "historical_prices/[%s]-historical-prices.csv" % (symbol)
            file = open(filename)

            file_content = file.read().splitlines()
            print("Symbol is:" + symbol)

            # header yung first 6
            counter = len(file_content) - 1

            while counter > 0:
                # pad for ez conversion
                line = file_content[counter].split(",")

                date = datetime.datetime.strptime(line[0], '%m/%d/%y').strftime('%Y-%m-%d') 
                price_open = line[1]
                price_high = line[2]
                price_low = line[3]
                price_close = line[4]
                volume = line[5]

                # # create open stock
                # StockDetail.objects.create(
                #     company=company,
                #     date_details=datetime_object_open,
                #     total_volume=volume,
                #     last_traded_price=price_open,
                #     percentage_change_close=1.000,
                #     indicator='U'
                # )

                # # create high stock
                # StockDetail.objects.create(
                #     company=company,
                #     date_details=datetime_object_high,
                #     total_volume=volume,
                #     last_traded_price=price_high,
                #     percentage_change_close=1.000,
                #     indicator='U'
                # )

                # # create low stock
                # StockDetail.objects.create(
                #     company=company,
                #     date_details=datetime_object_low,
                #     total_volume=volume,
                #     last_traded_price=price_low,
                #     percentage_change_close=1.000,
                #     indicator='U'
                # )

                # # create close stock
                # StockDetail.objects.create(
                #     company=company,
                #     date_details=datetime_object_close,
                #     total_volume=volume,
                #     last_traded_price=price_close,
                #     percentage_change_close=1.000,
                #     indicator='U'
                # )

                stockpricetoday = StockPrice.objects.filter(company=company, date_details=date).first()

                if stockpricetoday is None:

                    StockPrice.objects.create(
                        company=company,
                        date_details=date,
                        open_price = price_open,
                        low_price = price_low,
                        high_price = price_high,
                        indicator = 'U',
                        percentage_change_close = 0,
                        total_volume = volume,
                        last_traded_price = price_close
                    )

                    print ("adding new date")

                else:

                    stockpricetoday.open_price  = price_open
                    stockpricetoday.high_price  = price_high
                    stockpricetoday.low_price  = price_low
                    stockpricetoday.last_traded_price  = price_close

                    stockpricetoday.save()

                counter = counter - 1

