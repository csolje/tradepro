import datetime
from operator import attrgetter

from django.http import JsonResponse

TIME_RANGE = 7


def get_daily_feed(company, from_datetime, to_datetime):
    start_day = from_datetime.date()
    end_day = to_datetime.date() + datetime.timedelta(1)
    print("getting [DAILY] stock from date %s to %s" % (str(start_day), str(end_day)))
    current_day = start_day
    bar_time = []
    close_prices = []
    opening_prices = []
    highest_prices = []
    lowest_prices = []
    volumes = []
    stocks = list(company.stockprice_set.filter(date_details__range=(start_day, end_day)))
    while current_day < end_day:

        current_stock_price = company.stockprice_set.filter(date_details=current_day).first() 

        if current_stock_price is not None:

            highest_price = current_stock_price.high_price
            lowest_price = current_stock_price.low_price
            opening_stock = current_stock_price.open_price
            closing_stock = current_stock_price.last_traded_price
            volume = current_stock_price.total_volume

            bar_time.append(int(current_day.strftime("%s")))

            if closing_stock is not None:
                close_prices.append(float(closing_stock))
            if opening_stock is not None:
                opening_prices.append(float(opening_stock))
            highest_prices.append(float(highest_price))
            lowest_prices.append(float(lowest_price))
            volumes.append(int(volume))

        current_day = current_day + datetime.timedelta(1)
    data = {
        "s": "ok",
        "t": bar_time,
        "c": close_prices,
        "o": opening_prices,
        "h": highest_prices,
        "l": lowest_prices,
        "v": volumes
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8')

def get_weekly_feed(company, from_datetime, to_datetime):
    start_day = from_datetime.date()
    end_day = to_datetime.date()
    current_week = start_day.isocalendar()[1]
    end_week = end_day.isocalendar()[1]
    bar_time = []
    close_prices = []
    opening_prices = []
    highest_prices = []
    lowest_prices = []
    volumes = []
    print("getting [WEEKLY] stock from date %s to %s" % (str(start_day), str(end_day)))
    stocks = list(company.stockdetail_set.filter(
        date_details__range=(start_day - datetime.timedelta(weeks=1),
                             end_day + datetime.timedelta(weeks=1))))
    while current_week < end_week:
        # get ISO week number
        week_stocks = [x for x in stocks if x.date_details.date().isocalendar()[1] == current_week]
        if len(week_stocks) > 0:
            highest_price = max(week_stocks, key=attrgetter('last_traded_price')).last_traded_price
            lowest_price = min(week_stocks, key=attrgetter('last_traded_price')).last_traded_price
            opening_stock = min(week_stocks, key=attrgetter('date_details')).last_traded_price
            closing_stock = max(week_stocks, key=attrgetter('date__details')).last_traded_price

            bar_time.append(int(current_week.strftime("%s")))

            if closing_stock is not None:
                close_prices.append(float(round(closing_stock, 4)))
                volumes.append(int(closing_stock.total_volume))
            if opening_stock is not None:
                opening_prices.append(float(round(opening_stock, 4)))
            highest_prices.append(float(round(highest_price, 4)))
            lowest_prices.append(float(round(lowest_price, 4)))

        current_week = current_week + 1
    data = {
        "s": "ok",
        "t": bar_time,
        "c": close_prices,
        "o": opening_prices,
        "h": highest_prices,
        "l": lowest_prices,
        # "v": volumes
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8')


def get_monthly_feed(company, from_datetime, to_datetime):
    start_day = from_datetime.date()
    end_day = to_datetime.date()
    current_month = start_day
    bar_time = []
    close_prices = []
    opening_prices = []
    highest_prices = []
    lowest_prices = []
    volumes = []
    stocks = list(company.stockdetail_set.filter(
        date_details__range=(start_day - datetime.timedelta(months=1),
                             end_day + datetime.timedelta(months=1))))
    print("getting [MONTHLY] stock from date %s to %s" % (str(start_day), str(end_day)))
    while current_month < end_day:
        month_stocks = [x for x in stocks if x.date_details.date().year == current_month.year and
                        x.date_details.date().month == current_month.month]
        if len(month_stocks) > 0:
            highest_price = max(month_stocks, key=attrgetter('last_traded_price')).last_traded_price
            lowest_price = min(month_stocks, key=attrgetter('last_traded_price')).last_traded_price
            opening_stock = min(month_stocks, key=attrgetter('date_details')).last_traded_price
            closing_stock = max(month_stocks, key=attrgetter('date__details')).last_traded_price

            bar_time.append(int(current_month.strftime("%s")))

            if closing_stock is not None:
                close_prices.append(float(round(closing_stock, 4)))
                volumes.append(int(closing_stock.total_volume))
            if opening_stock is not None:
                opening_prices.append(float(round(opening_stock, 4)))
            highest_prices.append(float(round(highest_price, 4)))
            lowest_prices.append(float(round(lowest_price, 4)))

        current_month = current_month + datetime.timedelta(months=1)
    data = {
        "s": "ok",
        "t": bar_time,
        "c": close_prices,
        "o": opening_prices,
        "h": highest_prices,
        "l": lowest_prices,
        # "v": volumes
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8')


def get_minute_feed(interval, company):
    print("getting [MINUTE] stock")
    now = datetime.datetime.now()
    bar_time = []
    close_prices = []
    opening_prices = []
    highest_prices = []
    lowest_prices = []
    start_time = now - datetime.timedelta(days=TIME_RANGE)
    stocks = list(company.stockdetail_set.filter(date_details__range=(start_time, now)))
    current_time = start_time
    if len(stocks) > 0:
        while current_time < now:
            stocks_by_interval = [x for x in stocks if x.date_details.replace(tzinfo=None) >= current_time and
                                  x.date_details.replace(tzinfo=None) <= current_time + datetime.timedelta(
                                      minutes=interval)]
            if len(stocks_by_interval) > 0:
                highest_price = max(stocks_by_interval, key=attrgetter('last_traded_price')).last_traded_price
                lowest_price = min(stocks_by_interval, key=attrgetter('last_traded_price')).last_traded_price
                opening_stock = min(stocks_by_interval, key=attrgetter('date_details')).last_traded_price
                closing_stock = max(stocks_by_interval, key=attrgetter('date_details')).last_traded_price

                stock_bartime = datetime.datetime(
                    year=current_time.year,
                    month=current_time.month,
                    day=current_time.day,
                    hour=current_time.hour,
                    minute=current_time.minute
                )
                bar_time.append(int(stock_bartime.strftime("%s")))

                highest_prices.append(float(round(highest_price, 2)))
                lowest_prices.append(float(round(lowest_price, 2)))

                if closing_stock is not None:
                    close_prices.append(float(round(closing_stock, 2)))
                if opening_stock is not None:
                    opening_prices.append(float(round(opening_stock, 2)))
                highest_prices.append(float(round(highest_price, 2)))
                lowest_prices.append(float(round(lowest_price, 2)))

            current_time = current_time + datetime.timedelta(minutes=interval)

    data = {
        "s": "ok",
        "t": bar_time,
        "c": close_prices,
        "o": opening_prices,
        "h": highest_prices,
        "l": lowest_prices,
        # "v": volumes
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8')


def get_hour_feed(interval, company):
    print("getting [HOUR] stock")
    now = datetime.datetime.now()
    bar_time = []
    close_prices = []
    opening_prices = []
    highest_prices = []
    lowest_prices = []
    start_time = now - datetime.timedelta(days=TIME_RANGE)
    stocks = list(company.stockdetail_set.filter(date_details__range=(start_time, now)))
    current_time = start_time
    if len(stocks) > 0:
        while current_time < now:
            stocks_by_interval = [x for x in stocks if x.date_details.replace(tzinfo=None) >= current_time and
                                  x.date_details.replace(tzinfo=None) <= current_time + datetime.timedelta(
                                      hours=interval)]
            if len(stocks_by_interval) > 0:
                highest_price = max(stocks_by_interval, key=attrgetter('last_traded_price')).last_traded_price
                lowest_price = min(stocks_by_interval, key=attrgetter('last_traded_price')).last_traded_price
                opening_stock = min(stocks_by_interval, key=attrgetter('date_details')).last_traded_price
                closing_stock = max(stocks_by_interval, key=attrgetter('date_details')).last_traded_price

                stock_bartime = datetime.datetime(
                    year=current_time.year,
                    month=current_time.month,
                    day=current_time.day,
                    hour=current_time.hour,
                    minute=current_time.minute
                )
                bar_time.append(int(stock_bartime.strftime("%s")))

                highest_prices.append(float(round(highest_price, 2)))
                lowest_prices.append(float(round(lowest_price, 2)))

                if closing_stock is not None:
                    close_prices.append(float(round(closing_stock, 2)))
                if opening_stock is not None:
                    opening_prices.append(float(round(opening_stock, 2)))
                highest_prices.append(float(round(highest_price, 2)))
                lowest_prices.append(float(round(lowest_price, 2)))

            current_time = current_time + datetime.timedelta(hours=interval)

    data = {
        "s": "ok",
        "t": bar_time,
        "c": close_prices,
        "o": opening_prices,
        "h": highest_prices,
        "l": lowest_prices,
        # "v": volumes
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8')
