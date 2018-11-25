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

		STOCK_PRICES = "http://phisix-api2.appspot.com/stocks.json"
		response = requests.get(STOCK_PRICES)
		json_response = response.json()
		list_length = len(json_response)

		indices = Index.objects.all()

		stocks = json_response['stock']
		datetime = json_response['as_of'].split("T")
		date = datetime[0]

		for stock in stocks:
			symbol = stock['symbol']
			volume = stock['volume']
			percent_change = stock['percent_change'] 

			if percent_change > 0:
				indicator="U"
			elif percent_change < 0:
				indicator="D"
			else:
				indicator="N"

			for index in indices:
				if index.security_symbol == symbol:
					index.total_volume = volume
					index.percentage_change_close = percent_change
					index.indicator = indicator

					index.save()


		for stock in stocks:
			symbol = stock['symbol']
			price = stock['price']
			price_amount = price['amount']
			percent_change = stock['percent_change'] 
			volume = stock['volume']
			company = Company.objects.filter(symbol=symbol).first()

			if company is not None:

				print (symbol)

				stockpricetoday = StockPrice.objects.filter(company=company, date_details=date).first()

				if percent_change > 0:
					indicator="U"
				elif percent_change < 0:
					indicator="D"
				else:
					indicator="N"

				if stockpricetoday is None:

					StockPrice.objects.create(
						company=company,
						date_details=date,
						open_price = price_amount,
						low_price = price_amount,
						high_price = price_amount,
						indicator = indicator,
						percentage_change_close = percent_change,
						total_volume = volume,
						last_traded_price = price_amount
					)

					print ("adding new date")

				else:

					print ("updating stockprices")

					stockpricetoday.total_volume = volume
					stockpricetoday.last_traded_price = price_amount
					stockpricetoday.percentage_change_close = percent_change

					previous_low = float(stockpricetoday.low_price)
					previous_high = float(stockpricetoday.high_price)
					compare = float(price_amount)

					if compare < previous_low:
						stockpricetoday.low_price = price_amount
					else:
						print ("no new low")

					if compare > previous_high:
						stockpricetoday.previous_high = price_amount
					else:
						print ("no new high")


					stockpricetoday.save()
