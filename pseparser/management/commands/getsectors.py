import os
import requests
import datetime
from django.core.management.base import LabelCommand, BaseCommand

from pseparser.models import Company, StockPrice, Index, Sector
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

        SECTORS = "http://mft-roi.com/udffeed/displaysectors/"

        response = requests.get(SECTORS)
        json_response = response.json()
        company_records = json_response['sector']

        for record in company_records:
            id_index = record['id_index']
            sector = Sector.objects.filter(id_index=id_index).first()
            if sector is None:
                print("creating company with alias: %s " % (id_index))
                Sector.objects.create(
                    id_index=id_index,
                    is_sectoral=record['is_sectoral'],
                    sort_order=record['sort_order'],
                    name=record['name'],
                    abbreviation=record['abbreviation'],
                    date_created=record['date_created'],
                )
               
            else:
                print("company already exist [%s]" % (id_index))

