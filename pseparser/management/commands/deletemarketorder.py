import os
import requests
import datetime
from django.core.management.base import LabelCommand, BaseCommand

from pseparser.models import Company, StockPrice, MarketOrder
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

        marketorder = MarketOrder.objects.all()

    

        for item in marketorder:

            item.delete()
            
            # company = item.company
            # stockprice = StockPrice.objects.filter(company=company).first()
            # price = stockprice.last_traded_price
            # pricecheck = item.price * 8
            # pricea = item.price

            # if pricecheck < price:
            #     item.price = pricecheck*10
            #     item.save()

            # if pricea > 4000:
            #     item.price = pricea/10000
            #     item.save()

