import os
import requests
from django.core.management.base import LabelCommand, BaseCommand

from pseparser.models import Company
from roi import settings

WSJ_URL = "http://quotes.wsj.com/PH/%s/historical-prices/download?num_rows=5000&range_days=5000&startDate=%s&endDate=%s"

WSJ_URL_TEST = "http://quotes.wsj.com/PH/BDO/historical-prices/download?num_rows=5000&range_days=5000&startDate=11/05/2014&endDate=02/03/2017"

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('start_date')
        parser.add_argument('end_date')

    def handle(self, *args, **options):

        start_date = options['start_date']
        end_date = options['end_date']
        # print("derp start:%s end:%s" % (start_date, end_date))
        # file_path = os.path.join(settings.MEDIA_ROOT, "hehe")
        companies = list(Company.objects.all());
        for company in companies:
            symbol = company.symbol
            print("downloading %s" % (symbol))
            self.download_file(WSJ_URL % (symbol, start_date, end_date ), "historical_prices/[%s]-historical-prices.csv" % (symbol))

    def download_file(self,url,local_destination):
        local_filename = local_destination
    # NOTE the stream=True parameter
        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    #f.flush() commented by recommendation from J.F.Sebastian
        return local_filename
