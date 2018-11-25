import os
import requests
import datetime
from django.core.management.base import LabelCommand, BaseCommand

from pseparser.models import Company, StockPrice, Index
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

        COMPANIES = "http://mft-roi.com/udffeed/displayall/"

        response = requests.get(COMPANIES)
        json_response = response.json()
        company_records = json_response['stocks']

        for record in company_records:
            symbol = record['symbol']
            company = Company.objects.filter(symbol=symbol).first()
            if company is None:
                print("creating company with alias: %s " % (symbol))
                Company.objects.create(
                    symbol=symbol,
                    symbol_id=record['symbol_id'],
                    company_id=record['company_id'],
                    security_name=record['security_name'],
                    company_name=record['company_name'],
                    security_status=record['security_status'],
                    listing_date=record['listing_date'],
                    security_type=record['security_type'],
                    subsector=record['subsector'],
                )
               
            else:
                print("company already exist [%s]" % (symbol))
