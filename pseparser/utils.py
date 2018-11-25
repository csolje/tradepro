from datetime import datetime
from pytz import timezone

def get_datetime_companylistingjson(datetimestring):
    return datetime.strptime(datetimestring, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone('Asia/Manila'))