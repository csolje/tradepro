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

        INDICES = "http://mft-roi.com/udffeed/displayindex/"

        response = requests.get(INDICES)
        json_response = response.json()
        company_records = json_response['index']

        for record in company_records:
            security_symbol = record['security_symbol']
            index = Index.objects.filter(security_symbol=security_symbol).first()
            if index is None:
                print("creating company with alias: %s " % (security_symbol))
                Index.objects.create(
                    security_symbol=security_symbol,
                    date_details=record['date_details'],
                    security_alias=record['security_alias'],
                    percentage_change_close=record['percentage_change_close'],
                    last_traded_price=record['last_traded_price'],
                    total_volume=record['total_volume'],
                    indicator=record['indicator'],
                )
               
            else:
                print("company already exist [%s]" % (security_symbol))

