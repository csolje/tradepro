import os
import requests
import datetime
from django.core.management.base import LabelCommand, BaseCommand

from pseparser.models import Company, StockPrice, Index, Sector, Subsector
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

        SUBSECTORS = "http://mft-roi.com/udffeed/displaysubsectors/"

        response = requests.get(SUBSECTORS)
        json_response = response.json()
        company_records = json_response['subsector']

        for record in company_records:
            id = record['id']
            subsector = Subsector.objects.filter(id=id).first()
            if subsector is None:
                print("creating company with alias: %s " % (id))
                Subsector.objects.create(
                    id=id,
                    name=record['name'],
                )
               
            else:
                print("company already exist [%s]" % (id))

