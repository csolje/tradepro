from django.core.mail import EmailMessage
from django.shortcuts import render, get_object_or_404
from django.template import Context
from django.template.loader import get_template

import requests as requests
import logging


from pseparser.models import *
from roi import settings
from .models import *
from datetime import datetime, date, timedelta
from .forms import *
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from django.db.models import Sum, Case, When, F, FloatField


LOGGER = logging.getLogger(__name__)



def fetch_stocks():
    STOCK_PRICES = "http://phisix-api2.appspot.com/stocks.json"

    STOCK_PRICES2 = "http://api.pse.tools/api/stocks"
    

    try:
        response = requests.get(STOCK_PRICES2)
        json_response = response.json()
        list_length = len(json_response)

        indices = Index.objects.all()
        stocks = json_response['data']

        datetime = json_response['timestamp'].split(" ")


        # response = requests.get(STOCK_PRICES)
        # json_response = response.json()
        # list_length = len(json_response)

        # indices = Index.objects.all()

        # stocks = json_response['stock']
        # datetime = json_response['as_of'].split("T")
        date = datetime[0]

        # for stock in stocks:
        #     symbol = stock['symbol']
        #     volume = stock['volume']
        #     percent_change = stock['percent_change'] 

        #     if percent_change > 0:
        #         indicator="U"
        #     elif percent_change < 0:
        #         indicator="D"
        #     else:
        #         indicator="N"

        #     for index in indices:
        #         if index.security_symbol == symbol:
        #             index.total_volume = volume
        #             index.percentage_change_close = percent_change
        #             index.indicator = indicator

        #             index.save()
        #             LOGGER.info("updating index")



        for stock in stocks:
            symbol = stock['symbol']
            
            open_price = stock['open']
            high_price = stock['high']
            low_price = stock['low']

            last_price = stock['last']
            changec = stock['change']
            
            if changec is not None:
                percent_change = float(stock['change'])

            volume = stock['volume']
            company = Company.objects.filter(symbol=symbol).first()

            if company is not None:

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
                        open_price = open_price,
                        low_price = low_price,
                        high_price = high_price,
                        indicator = indicator,
                        percentage_change_close = percent_change,
                        total_volume = volume,
                        last_traded_price = last_price
                    )

                    print ("adding new date for")

                else:
                    stockpricetoday.total_volume = volume
                    stockpricetoday.indicator = indicator
                    stockpricetoday.last_traded_price = last_price
                    stockpricetoday.percentage_change_close = percent_change

                    stockpricetoday.low_price = low_price
                    stockpricetoday.high_price = high_price
                    

                    # LOGGER.info("updating price")

                    print ("updating")


                    stockpricetoday.save()

    except:  # This is the correct syntax        print ("error")
        print ("error")

# Create your views here.
@login_required(login_url='login')
def index(request):

    fetch_stocks()

    


    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    client = request.user.client

    alerts = client.alert_set.filter(seen=0)

    for alert in alerts:
        alert.seen = 1
        alert.save()

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}

    for item in sold:
        company = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company] = item

    portfolio = {}
    total_stock_value = 0

    for item in bought:
        company = Company.objects.get(symbol=item['stock__symbol'])
        if company in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company]['units']
            item['price'] = item['price'] - sold_stocks[company]['price']
            available_stocks = client.order_set.filter(method='B',stock=company).exclude(
                status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).order_by('id')
            number_of_stocks_sold = sold_stocks[company]['units']

            #filter remaining stock
            last_stock_price = 0
            last_stock_units = 0
            units_remaining = 0

            for this_stock in available_stocks:
                if number_of_stocks_sold >= this_stock.units:
                    available_stocks = available_stocks.exclude(id=this_stock.id)
                number_of_stocks_sold = number_of_stocks_sold - this_stock.units
                if(number_of_stocks_sold <= 0):
                    last_stock_price = this_stock.price
                    last_stock_units = this_stock.units
                    units_remaining = number_of_stocks_sold*-1
                    available_stocks = available_stocks.exclude(id=this_stock.id)
                    break

            last_price_per_unit = (last_stock_price/last_stock_units)
            sum_price = available_stocks.aggregate(sum_price=Sum('price'))['sum_price']

            if sum_price:
                sum_price = float(sum_price) + float(last_price_per_unit*units_remaining)
            else:
                sum_price = float(last_price_per_unit*units_remaining)

            item['price'] = sum_price



        if item['units'] > 0:

            item['stockprice'] = company.stockprice_set.order_by('-date_details').first()
            
            latest_stock_item = company.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company] = item


            lastclose=float(latest_stock_item.last_traded_price)/((float(latest_stock_item.percentage_change_close)/100)+1)
            item['change']=float(latest_stock_item.last_traded_price)-lastclose


    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    order_set = client.order_set.order_by('-id')

    wallet_set = client.transaction_set.order_by('-id')

    

    companies_array = []

    companiesfeed = Company.objects.order_by('symbol')
    for company_feed in companiesfeed:
        stockprice = StockPrice.objects.filter(company=company_feed).last()
        if stockprice is not None:
            companies_array.append({'stock':company_feed, 'value':(stockprice.total_volume*stockprice.last_traded_price), 'volume':stockprice.total_volume, 'change':stockprice.percentage_change_close, 'lastprice':stockprice.last_traded_price})


    losers = sorted(companies_array, key=lambda k: k['change'])[:10]
    winners = sorted(companies_array, key=lambda k: k['change'], reverse=True)[:10]
    active = sorted(companies_array, key=lambda k: k['value'], reverse=True)[:10]


    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company] = item
        



    for item in portfolio:
        company = Company.objects.get(symbol=item.symbol)
        
        if company in today_stocks:

            stock_item = company.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company]['units'] - today_stocks[company]['units']
            today_ex_portfolio_price = portfolio[company]['price'] - today_stocks[company]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company.stockprice_set.last()

            stock_change = portfolio[company]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change

    if request.method == 'GET':
        client = request.user.client
        pse = Index.objects.get(security_symbol="PSE")
        indices = Index.objects.all()

        try:
            STOCK_PRICES = "http://phisix-api2.appspot.com/stocks.json"
            response = requests.get(STOCK_PRICES)
            json_response = response.json()
            as_of = json_response['as_of']


            if as_of is not None:

                stocks = json_response['stock']

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
        except:  # This is the correct syntax        print ("error")
            print ("error")

        contact = ContactForm();

        # localization
        folder = 'client/en/'  # default EN

        if client.language == 'ja':
            folder = 'client/ja/'
        elif client.language == 'kr':
            folder = 'client/kr/'

        return render(request, str(folder + 'index.html'),
                      {'alerts':alerts, 'marketstatus': marketstatus, 'losers': losers, 'winners': winners, 'active':active, 'client': client, 'pse': pse, 'indices': indices, 'contact': contact, 'recent_change':recent_change, 'total_stock_value':total_stock_value})

    elif request.method == 'POST':
        form = ContactForm(request.POST)
        user = request.user
        if form.is_valid():
            data = form.cleaned_data
            subject = data['subject']
            content = data['content']

            # Email the profile with the
            # contact information
            template = get_template('contact_template.txt')

            context = Context({
                'content': content,
            })

            email_body = template.render(context)

            if (user.email is not None):
                EmailMessage(
                    subject='test',
                    body=email_body,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[user.email]
                ).send()

            EmailMessage(
                subject=subject,
                body=email_body,
                from_email=settings.EMAIL_HOST_USER,
                to=settings.ROI_RECIPIENTS,
                headers={'Reply-To': user.email}
            ).send()

            return HttpResponseRedirect('/')


@login_required(login_url='login')
def watchlist(request):

    fetch_stocks()


    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    client = request.user.client

    alerts = client.alert_set.filter(seen=0)

    for alert in alerts:
        alert.seen = 1
        alert.save()


    watchlistacct = Client.objects.get(id=2)

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}

    for item in sold:
        company = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company] = item

    portfolio = {}
    total_stock_value = 0

    for item in bought:
        company = Company.objects.get(symbol=item['stock__symbol'])
        if company in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company]['units']
            item['price'] = item['price'] - sold_stocks[company]['price']
            available_stocks = client.order_set.filter(method='B',stock=company).exclude(
                status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).order_by('id')
            number_of_stocks_sold = sold_stocks[company]['units']

            #filter remaining stock
            last_stock_price = 0
            last_stock_units = 0
            units_remaining = 0

            for this_stock in available_stocks:
                if number_of_stocks_sold >= this_stock.units:
                    available_stocks = available_stocks.exclude(id=this_stock.id)
                number_of_stocks_sold = number_of_stocks_sold - this_stock.units
                if(number_of_stocks_sold <= 0):
                    last_stock_price = this_stock.price
                    last_stock_units = this_stock.units
                    units_remaining = number_of_stocks_sold*-1
                    available_stocks = available_stocks.exclude(id=this_stock.id)
                    break

            last_price_per_unit = (last_stock_price/last_stock_units)
            sum_price = available_stocks.aggregate(sum_price=Sum('price'))['sum_price']

            if sum_price:
                sum_price = float(sum_price) + float(last_price_per_unit*units_remaining)
            else:
                sum_price = float(last_price_per_unit*units_remaining)

            item['price'] = sum_price



        if item['units'] > 0:

            item['stockprice'] = company.stockprice_set.order_by('-date_details').first()
            
            latest_stock_item = company.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company] = item


            lastclose=float(latest_stock_item.last_traded_price)/((float(latest_stock_item.percentage_change_close)/100)+1)
            item['change']=float(latest_stock_item.last_traded_price)-lastclose


    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    order_set = client.order_set.order_by('-id')

    wallet_set = client.transaction_set.order_by('-id')

    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company] = item

        

    for item in portfolio:
        company = Company.objects.get(symbol=item.symbol)
        
        if company in today_stocks:

            stock_item = company.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company]['units'] - today_stocks[company]['units']
            today_ex_portfolio_price = portfolio[company]['price'] - today_stocks[company]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company.stockprice_set.last()

            stock_change = portfolio[company]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change


    if request.method == 'GET':
        client = request.user.client

        contact = ContactForm();

        # localization
        folder = 'client/en/'  # default EN

        if client.language == 'ja':
            folder = 'client/ja/'
        elif client.language == 'kr':
            folder = 'client/kr/'

        return render(request, str(folder + 'watchlist.html'), {'alerts':alerts, 'marketstatus': marketstatus, 'watchlistacct': watchlistacct, 'client': client, 'contact': contact, 'recent_change':recent_change, 'total_stock_value':total_stock_value})

    elif request.method == 'POST':
        form = ContactForm(request.POST)
        user = request.user
        if form.is_valid():
            data = form.cleaned_data
            subject = data['subject']
            content = data['content']

            # Email the profile with the
            # contact information
            template = get_template('contact_template.txt')

            context = Context({
                'content': content,
            })

            email_body = template.render(context)

            if (user.email is not None):
                EmailMessage(
                    subject='test',
                    body=email_body,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[user.email]
                ).send()

            EmailMessage(
                subject=subject,
                body=email_body,
                from_email=settings.EMAIL_HOST_USER,
                to=settings.ROI_RECIPIENTS,
                headers={'Reply-To': user.email}
            ).send()

            return HttpResponseRedirect('/')


@login_required(login_url='login')
def stock(request, symbol):

    fetch_stocks()

    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    client = request.user.client

    alerts = client.alert_set.filter(seen=0)

    for alert in alerts:
        alert.seen = 1
        alert.save()

    pse = Index.objects.get(security_symbol="PSE")
    symbol = symbol.upper()
    company = get_object_or_404(Company, symbol=symbol)
    latest_stock = company.stockprice_set.order_by('-date_details').first()
    subsector = get_object_or_404(Subsector, id=company.subsector)
    total_value = latest_stock.total_volume * latest_stock.last_traded_price
    change_in_points = latest_stock.last_traded_price * (latest_stock.percentage_change_close / 100)

    contact = ContactForm();

    open_price=latest_stock.open_price
    high_price=latest_stock.high_price
    low_price=latest_stock.low_price
    last_price=latest_stock.last_traded_price
    percent_change=latest_stock.percentage_change_close

    close_price= latest_stock.last_traded_price/((percent_change/100)+1)
    change=last_price-close_price

    change_float = float(change)

    if change_float > 0:
        indicator="U"
    elif change_float < 0:
        indicator="D"
    else:
        indicator="N"


    # credit_stocks = request.user.client.order_set.all().filter(method='B')#.aggregate(Sum('price'))
    # debit_stocks = request.user.client.order_set.all().filter(method='S')#.aggregate(Sum('price'))

    price = round(latest_stock.last_traded_price, 4)
    if price and price <= 0.0099:
        lot_size = 1000000
        tick_size = 0.0001
    elif price >= 0.0100 and price <= 0.0490:
        lot_size = 100000
        tick_size = 0.005
    elif price >= 0.0500 and price <= 0.4900:
        lot_size = 10000
        tick_size = 0.005
    elif price >= 0.50 and price <= 4.99:
        lot_size = 1000
        tick_size = 0.01
    elif price >= 5.00 and price <= 9.99:
        lot_size = 100
        tick_size = 0.01
    elif price >= 10.00 and price <= 19.99:
        lot_size = 100
        tick_size = 0.02
    elif price >= 20.00 and price <= 49.99:
        lot_size = 100
        tick_size = 0.05
    elif price >= 50.00 and price <= 99.99:
        lot_size = 10
        tick_size = 0.05
    elif price >= 100.00 and price <= 199.99:
        lot_size = 10
        tick_size = 0.10
    elif price >= 200.00 and price <= 499.99:
        lot_size = 10
        tick_size = 0.20
    elif price >= 500.00 and price <= 999.99:
        lot_size = 10
        tick_size = 0.50
    elif price >= 1000.00 and price <= 1999.99:
        lot_size = 5
        tick_size = 1.00
    elif price >= 2000.00 and price <= 4998.99:
        lot_size = 5
        tick_size = 2.00
    else:
        lot_size = 5
        tick_size = 5.00


    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}

    for item in sold:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company_item] = item

    portfolio = {}
    total_stock_value = 0

    for item in bought:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        if company_item in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company_item]['units']
            item['price'] = item['price'] - sold_stocks[company_item]['price']
        if item['units'] > 0:

            item['stockprice'] = company_item.stockprice_set.order_by('-date_details').first()

            latest_stock_item = company_item.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company_item] = item

    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company_item] = item

        

    for item in portfolio:
        company_item = Company.objects.get(symbol=item.symbol)
        
        if company_item in today_stocks:

            stock_item = company_item.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company_item]['units'] - today_stocks[company_item]['units']
            today_ex_portfolio_price = portfolio[company_item]['price'] - today_stocks[company_item]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company_item]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company_item]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company_item.stockprice_set.last()

            stock_change = portfolio[company_item]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change




    if request.method == 'POST':
        form = AddToWatchlistForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['add'] == 1:
                request.user.client.watchlist.add(company)
            else:
                request.user.client.watchlist.remove(company)
            return HttpResponseRedirect(reverse('client:stock', args=(symbol,)))

    else:
        form = AddToWatchlistForm()

    # localization
    folder = 'client/en/'  # default EN

    if client.language == 'ja':
        folder = 'client/ja/'
    elif client.language == 'kr':
        folder = 'client/kr/'

    return render(request, str(folder + 'stock.html'),
                  {'alerts': alerts, 'marketstatus': marketstatus, 'client': client, 'pse': pse, 'symbol': symbol, 'form': form, 'company': company,
                   'latest_stock': latest_stock, 'subsector': subsector, 'total_value': total_value, 'recent_change': recent_change, 'total_stock_value': total_stock_value,
                   'lot_size': lot_size, 'tick_size': tick_size, 'contact': contact, 'open_price':open_price, 'high_price':high_price, 'low_price':low_price, 'close_price':close_price, 'last_price':last_price, 'change':change, 'percent_change':percent_change, 'indicator':indicator})

@login_required(login_url='login')
def buy(request, symbol):

    fetch_stocks()

    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    company = get_object_or_404(Company, symbol=symbol)
    pse = Index.objects.get(security_symbol="PSE")
    latest_stock = company.stockprice_set.order_by('-date_details').first()
    subsector = get_object_or_404(Subsector, id=company.subsector)
    total_value = latest_stock.total_volume * latest_stock.last_traded_price
    change_in_points = latest_stock.last_traded_price * (latest_stock.percentage_change_close / 100)

    contact = ContactForm();

    open_price=latest_stock.open_price
    high_price=latest_stock.high_price
    low_price=latest_stock.low_price
    last_price=latest_stock.last_traded_price
    percent_change=latest_stock.percentage_change_close

    close_price= latest_stock.last_traded_price/((percent_change/100)+1)
    change=last_price-close_price

    change_float = float(change)

    if change_float > 0:
        indicator="U"
    elif change_float < 0:
        indicator="D"
    else:
        indicator="N"


    client = get_object_or_404(Client, user=request.user)

    alerts = client.alert_set.filter(seen=0)

    for alert in alerts:
        alert.seen = 1
        alert.save()

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}


    bid_set = company.marketorder_set.filter(order_type='b').order_by('-price')[:200]
    con_bid_set = []

    current_bidprice = 0
    current_bidunits = 0
    current_bidqty = 0
    i = -1

    for bid in bid_set:
        if bid.price <= last_price:
            if bid.price != current_bidprice:
                current_bidprice = bid.price
                currentbid = {'units':int(bid.units), 'price':bid.price, 'qty':1}
                con_bid_set.append(currentbid)
                i = i + 1
            else:
                con_bid_set[i]['units'] = con_bid_set[i]['units'] + int(bid.units)
                con_bid_set[i]['qty'] = con_bid_set[i]['qty'] + 1

    con_bid_set = con_bid_set[:10]


    ask_set = company.marketorder_set.filter(order_type='a').order_by('price')[:200]

    con_ask_set = []

    current_askprice = 0
    current_askunits = 0
    current_askqty = 0
    j = -1

    for ask in ask_set:
        if ask.price >= last_price:
            if ask.price != current_askprice:
                current_askprice = ask.price
                currentask = {'units':int(ask.units), 'price':ask.price, 'qty':1}
                con_ask_set.append(currentask)
                j = j + 1
            else:
                con_ask_set[j]['units'] = con_ask_set[j]['units'] + int(ask.units)
                con_ask_set[j]['qty'] = con_ask_set[j]['qty'] + 1

    con_ask_set = con_ask_set[:10]

    for item in sold:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company_item] = item

    portfolio = {}
    total_stock_value = 0

    for item in bought:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        if company_item in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company_item]['units']
            item['price'] = item['price'] - sold_stocks[company_item]['price']
        if item['units'] > 0:

            item['stockprice'] = company_item.stockprice_set.order_by('-date_details').first()

            latest_stock_item = company_item.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company_item] = item

    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():

            # Transaction.objects.create(
            #     amount=(form.cleaned_data['price']+form.cleaned_data['charge'])*(-1),
            #     client=client,
            #     order_type='B',
            #     note='Buy ' + str(company.symbol),
            # )


            client = form.cleaned_data['client']
            client.wallet = client.wallet - (form.cleaned_data['price'] + form.cleaned_data['charge'])



            client.save()
            form.save()

            EmailMessage(
                subject='(V2) Buy Order from ' + str(client.user),
                body= 'Buy ' + str(client.user) + " with " + str(company.symbol) + " for " + str(form.cleaned_data['price']/form.cleaned_data['units']) + " for " +  str(form.cleaned_data['units']) + " units " + str(client.wallet),
                from_email=settings.EMAIL_HOST_USER,
                to=settings.EDIT_RECIPIENTS
            ).send()

            company_item = Company.objects.get(symbol=item['stock__symbol'])

            currentorder = client.order_set.order_by('-date_created').first()
            AdminNotification.objects.create(
                client=client,
                order=currentorder.id,
                message = str(client.user) + ' Bought ' + str(company.symbol) + ' # ' + str(currentorder.id)
            )


            # return HttpResponseRedirect(reverse('client:stock', args=(symbol,)))
            return HttpResponseRedirect(reverse('client:portfolio'))




    else:
        form = OrderForm()

    price = round(latest_stock.last_traded_price, 4)
    if close_price and close_price <= 0.0099:
        lot_size = 1000000
        tick_size = 0.0001
    elif close_price >= 0.0100 and close_price <= 0.0490:
        lot_size = 100000
        tick_size = 0.005
    elif close_price >= 0.0500 and close_price <= 0.4900:
        lot_size = 10000
        tick_size = 0.005
    elif close_price >= 0.50 and close_price <= 4.99:
        lot_size = 1000
        tick_size = 0.01
    elif close_price >= 5.00 and close_price <= 9.99:
        lot_size = 100
        tick_size = 0.01
    elif close_price >= 10.00 and close_price <= 19.99:
        lot_size = 100
        tick_size = 0.02
    elif close_price >= 20.00 and close_price <= 49.99:
        lot_size = 100
        tick_size = 0.05
    elif close_price >= 50.00 and close_price <= 99.99:
        lot_size = 10
        tick_size = 0.05
    elif close_price >= 100.00 and close_price <= 199.99:
        lot_size = 10
        tick_size = 0.10
    elif close_price >= 200.00 and close_price <= 499.99:
        lot_size = 10
        tick_size = 0.20
    elif close_price >= 500.00 and close_price <= 999.99:
        lot_size = 10
        tick_size = 0.50
    elif close_price >= 1000.00 and close_price <= 1999.99:
        lot_size = 5
        tick_size = 1.00
    elif close_price >= 2000.00 and close_price <= 4998.99:
        lot_size = 5
        tick_size = 2.00
    else:
        lot_size = 5
        tick_size = 5.00

    
    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company_item] = item

        

    for item in portfolio:
        company_item = Company.objects.get(symbol=item.symbol)
        
        if company_item in today_stocks:

            stock_item = company_item.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company_item]['units'] - today_stocks[company_item]['units']
            today_ex_portfolio_price = portfolio[company_item]['price'] - today_stocks[company_item]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company_item]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company_item]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company_item.stockprice_set.last()

            stock_change = portfolio[company_item]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change


    # localization
    folder = 'client/en/'  # default EN

    if client.language == 'ja':
        folder = 'client/ja/'
    elif client.language == 'kr':
        folder = 'client/kr/'

    return render(request, str(folder + 'buy.html'),
                  {'alerts':alerts, 'marketstatus': marketstatus, 'form': form, 'pse': pse, 'symbol': symbol, 'bid_set': con_bid_set, 'ask_set': con_ask_set, 'company': company, 'latest_stock': latest_stock,
                   'subsector': subsector, 'total_value': total_value, 'change_in_points': change_in_points,
                   'client': client, 'total_stock_value': total_stock_value, 'recent_change': recent_change,
                   'pending_stocks': pending_stocks, 'lot_size': lot_size, 'portfolio': portfolio,
                   'tick_size': tick_size, 'today_transactions': today_transactions, 'contact': contact, 'open_price':open_price, 'high_price':high_price, 'low_price':low_price, 'close_price':close_price, 'last_price':last_price, 'change':change, 'percent_change':percent_change, 'indicator':indicator})


@login_required(login_url='login')
def sell(request, symbol):

    fetch_stocks()

    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    company = get_object_or_404(Company, symbol=symbol)
    pse = Index.objects.get(security_symbol="PSE")
    latest_stock = company.stockprice_set.order_by('-date_details').first()
    subsector = get_object_or_404(Subsector, id=company.subsector)
    total_value = latest_stock.total_volume * latest_stock.last_traded_price
    change_in_points = latest_stock.last_traded_price * (latest_stock.percentage_change_close / 100)

    contact = ContactForm();

    open_price=latest_stock.open_price
    high_price=latest_stock.high_price
    low_price=latest_stock.low_price
    last_price=latest_stock.last_traded_price
    percent_change=latest_stock.percentage_change_close

    close_price= latest_stock.last_traded_price/((percent_change/100)+1)
    change=last_price-close_price

    change_float = float(change)

    if change_float > 0:
        indicator="U"
    elif change_float < 0:
        indicator="D"
    else:
        indicator="N"

    client = get_object_or_404(Client, user=request.user)

    alerts = client.alert_set.filter(seen=0)

    for alert in alerts:
        alert.seen = 1
        alert.save()

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}

    for item in sold:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company_item] = item

    portfolio = {}
    total_stock_value = 0
 
    for item in bought:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        if company_item in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company_item]['units']
            item['price'] = item['price'] - sold_stocks[company_item]['price']
        if item['units'] >= 0:

            item['stockprice'] = company_item.stockprice_set.order_by('-date_details').first()
            
            latest_stock_item = company_item.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company_item] = item

    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    owned_stocks = portfolio[company]

    bid_set = company.marketorder_set.filter(order_type='b').order_by('-price')[:200]
    con_bid_set = []

    current_bidprice = 0
    current_bidunits = 0
    current_bidqty = 0
    i = -1

    for bid in bid_set:
        if bid.price != current_bidprice:
            current_bidprice = bid.price
            currentbid = {'units':int(bid.units), 'price':bid.price, 'qty':1}
            con_bid_set.append(currentbid)
            i = i + 1
        else:
            con_bid_set[i]['units'] = con_bid_set[i]['units'] + int(bid.units)
            con_bid_set[i]['qty'] = con_bid_set[i]['qty'] + 1

    con_bid_set = con_bid_set[:10]


    ask_set = company.marketorder_set.filter(order_type='a').order_by('price')[:200]

    con_ask_set = []

    current_askprice = 0
    current_askunits = 0
    current_askqty = 0
    j = -1

    for ask in ask_set:
        if ask.price != current_askprice:
            current_askprice = ask.price
            currentask = {'units':int(ask.units), 'price':ask.price, 'qty':1}
            con_ask_set.append(currentask)
            j = j + 1
        else:
            con_ask_set[j]['units'] = con_ask_set[j]['units'] + int(ask.units)
            con_ask_set[j]['qty'] = con_ask_set[j]['qty'] + 1

    con_ask_set = con_ask_set[:10]


    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            form.save()
            EmailMessage(
                subject='(V2) Sell Order from ' + str(client.user),
                body= 'Buy ' + str(client.user) + " with " + str(company.symbol) + " for " + str(form.cleaned_data['price']/form.cleaned_data['units']) + " for " +  str(form.cleaned_data['units']) + " units " + str(client.wallet),
                from_email=settings.EMAIL_HOST_USER,
                to=settings.EDIT_RECIPIENTS
            ).send()

            currentorder = client.order_set.order_by('-date_created').first()
            AdminNotification.objects.create(
                client=client,
                order=currentorder.id,
                message = str(client.user) + ' Sold ' + str(company.symbol) + ' # ' + str(currentorder.id)
            )

            # return HttpResponseRedirect(reverse('client:stock', args=(symbol,)))
            return HttpResponseRedirect(reverse('client:portfolio'))

    else:
        form = OrderForm()

    price = round(latest_stock.last_traded_price, 4)
    if close_price and close_price <= 0.0099:
        lot_size = 1000000
        tick_size = 0.0001
    elif close_price >= 0.0100 and close_price <= 0.0490:
        lot_size = 100000
        tick_size = 0.005
    elif close_price >= 0.0500 and close_price <= 0.4900:
        lot_size = 10000
        tick_size = 0.005
    elif close_price >= 0.50 and close_price <= 4.99:
        lot_size = 1000
        tick_size = 0.01
    elif close_price >= 5.00 and close_price <= 9.99:
        lot_size = 100
        tick_size = 0.01
    elif close_price >= 10.00 and close_price <= 19.99:
        lot_size = 100
        tick_size = 0.02
    elif close_price >= 20.00 and close_price <= 49.99:
        lot_size = 100
        tick_size = 0.05
    elif close_price >= 50.00 and close_price <= 99.99:
        lot_size = 10
        tick_size = 0.05
    elif close_price >= 100.00 and close_price <= 199.99:
        lot_size = 10
        tick_size = 0.10
    elif close_price >= 200.00 and close_price <= 499.99:
        lot_size = 10
        tick_size = 0.20
    elif close_price >= 500.00 and close_price <= 999.99:
        lot_size = 10
        tick_size = 0.50
    elif close_price >= 1000.00 and close_price <= 1999.99:
        lot_size = 5
        tick_size = 1.00
    elif close_price >= 2000.00 and close_price <= 4998.99:
        lot_size = 5
        tick_size = 2.00
    else:
        lot_size = 5
        tick_size = 5.00

    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company_item] = item

        

    for item in portfolio:
        company_item = Company.objects.get(symbol=item.symbol)
        
        if company_item in today_stocks:

            stock_item = company_item.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company_item]['units'] - today_stocks[company_item]['units']
            today_ex_portfolio_price = portfolio[company_item]['price'] - today_stocks[company_item]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company_item]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company_item]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company_item.stockprice_set.last()

            stock_change = portfolio[company_item]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change

    sell_transactions = Order.objects.all().filter(client__user=request.user, method='S',
                                                   status__in=['Pen', 'Par', 'Rev'])

    # localization
    folder = 'client/en/'  # default EN

    if client.language == 'ja':
        folder = 'client/ja/'
    elif client.language == 'kr':
        folder = 'client/kr/'

    return render(request, str(folder + 'sell.html'),
                  {'alerts':alerts, 'marketstatus': marketstatus, 'form': form, 'pse': pse, 'sell': True, 'symbol': symbol, 'bid_set': con_bid_set, 'ask_set': con_ask_set, 'company': company,
                   'latest_stock': latest_stock, 'subsector': subsector, 'total_value': total_value,
                   'change_in_points': change_in_points, 'client': client, 'recent_change': recent_change,
                   'total_stock_value': total_stock_value, 'pending_stocks': pending_stocks,
                   'owned_stocks': owned_stocks, 'portfolio': portfolio, 'lot_size': lot_size, 'tick_size': tick_size,
                   'today_transactions': today_transactions, 'sell_transactions': sell_transactions,
                   'contact': contact, 'open_price':open_price, 'high_price':high_price, 'low_price':low_price, 'close_price':close_price, 'last_price':last_price, 'change':change, 'percent_change':percent_change, 'indicator':indicator})


@login_required(login_url='login')
def edit_order(request, order_id):
    

    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    client = request.user.client
    order = Order.objects.get(id=order_id)
    pse = Index.objects.get(security_symbol="PSE")
    old_price = order.price
    old_status = order.status
    old_charge = order.charge
    company = order.stock
    latest_stock = company.stockprice_set.order_by('-date_details').first()
    subsector = get_object_or_404(Subsector, id=company.subsector)
    total_value = latest_stock.total_volume * latest_stock.last_traded_price
    change_in_points = latest_stock.last_traded_price * (latest_stock.percentage_change_close / 100)

    contact = ContactForm();

    open_price=latest_stock.open_price
    high_price=latest_stock.high_price
    low_price=latest_stock.low_price
    last_price=latest_stock.last_traded_price
    percent_change=latest_stock.percentage_change_close

    close_price= latest_stock.last_traded_price/((percent_change/100)+1)
    change=last_price-close_price

    change_float = float(change)

    if change_float > 0:
        indicator="U"
    elif change_float < 0:
        indicator="D"
    else:
        indicator="N"

    price = round(latest_stock.last_traded_price, 4)
    if price and price <= 0.0099:
        lot_size = 1000000
        tick_size = 0.0001
    elif price >= 0.0100 and price <= 0.0490:
        lot_size = 100000
        tick_size = 0.005
    elif price >= 0.0500 and price <= 0.4900:
        lot_size = 10000
        tick_size = 0.005
    elif price >= 0.50 and price <= 4.99:
        lot_size = 1000
        tick_size = 0.01
    elif price >= 5.00 and price <= 9.99:
        lot_size = 100
        tick_size = 0.01
    elif price >= 10.00 and price <= 19.99:
        lot_size = 100
        tick_size = 0.02
    elif price >= 20.00 and price <= 49.99:
        lot_size = 100
        tick_size = 0.05
    elif price >= 50.00 and price <= 99.99:
        lot_size = 10
        tick_size = 0.05
    elif price >= 100.00 and price <= 199.99:
        lot_size = 10
        tick_size = 0.10
    elif price >= 200.00 and price <= 499.99:
        lot_size = 10
        tick_size = 0.20
    elif price >= 500.00 and price <= 999.99:
        lot_size = 10
        tick_size = 0.50
    elif price >= 1000.00 and price <= 1999.99:
        lot_size = 5
        tick_size = 1.00
    elif price >= 2000.00 and price <= 4998.99:
        lot_size = 5
        tick_size = 2.00
    else:
        lot_size = 5
        tick_size = 5.00

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}

    for item in sold:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company_item] = item

    portfolio = {}
    total_stock_value = 0

    for item in bought:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        if company_item in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company_item]['units']
            item['price'] = item['price'] - sold_stocks[company_item]['price']
        if item['units'] > 0:

            item['stockprice'] = company_item.stockprice_set.order_by('-date_details').first()

            latest_stock_item = company_item.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company_item] = item

    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company_item] = item

        

    for item in portfolio:
        company_item = Company.objects.get(symbol=item.symbol)
        
        if company_item in today_stocks:

            stock_item = company_item.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company_item]['units'] - today_stocks[company_item]['units']
            today_ex_portfolio_price = portfolio[company_item]['price'] - today_stocks[company_item]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company_item]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company_item]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company_item.stockprice_set.last()

            stock_change = portfolio[company_item]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change


    contact = ContactForm();

    if request.method == 'POST':
        form = EditOrderForm(request.POST, instance=order)
        if form.is_valid():
            price_difference = old_price - form.cleaned_data['price']
            client = order.client
            if order.method == 'B':
                if form.cleaned_data['status'] == 'Can' and old_status != 'Can':
                    client.wallet = client.wallet + old_price + old_charge
                    EmailMessage(
                        subject='Order Cancelled ' + str(order.client.user),
                        body= str(order.client.user) + ' Cancelled ' + str(company.symbol),
                        from_email=settings.EMAIL_HOST_USER,
                        to=settings.EDIT_RECIPIENTS
                    ).send()

                    AdminNotification.objects.create(
                        client=client,
                        order=order.id,
                        message = str(order.client.user) + ' Cancelled Buy for ' + str(company.symbol) + ' # ' + str(order.id)
                    )

                elif form.cleaned_data['status'] == 'Pen':
                    client.wallet = client.wallet + price_difference
                    EmailMessage(
                        subject='Order Revised ' + str(order.client.user),
                        body= 'Revised order from ' + str(order.client.user) + " with " + str(company.symbol),
                        from_email=settings.EMAIL_HOST_USER,
                        to=settings.EDIT_RECIPIENTS
                    ).send()

                    AdminNotification.objects.create(
                        client=client,
                        order=order.id,
                        message = str(order.client.user) + ' Revised Buy for ' + str(company.symbol) + ' # ' + str(order.id)
                    )

            elif order.method == 'S': 
                if form.cleaned_data['status'] == 'Can' and old_status != 'Can':
                    EmailMessage(
                        subject='Order Cancelled ' + str(order.client.user),
                        body= str(order.client.user) + ' Cancelled ' + str(company.symbol),
                        from_email=settings.EMAIL_HOST_USER,
                        to=settings.EDIT_RECIPIENTS
                    ).send()

                    AdminNotification.objects.create(
                        client=client,
                        order=order.id,
                        message = str(order.client.user) + ' Cancelled Sell for ' + str(company.symbol) + ' # ' + str(order.id)
                    )


                elif form.cleaned_data['status'] == 'Pen':
                    EmailMessage(
                        subject='Order Revised ' + str(order.client.user),
                        body= 'Revised order from ' + str(order.client.user) + " with " + str(company.symbol),
                        from_email=settings.EMAIL_HOST_USER,
                        to=settings.EDIT_RECIPIENTS
                    ).send()

                    AdminNotification.objects.create(
                        client=client,
                        order=order.id,
                        message = str(order.client.user) + ' Revised Sell for ' + str(company.symbol) + ' # ' + str(order.id)
                    )

            client.save()
            form.save()

            return HttpResponseRedirect(reverse('client:portfolio'))
    else:
        form = EditOrderForm(instance=order)



        

    # localization
    folder = 'client/en/'  # default EN

    if client.language == 'ja':
        folder = 'client/ja/'
    elif client.language == 'kr':
        folder = 'client/kr/'

    return render(request, str(folder + 'edit_order.html'),
                  {'marketstatus': marketstatus, 'form': form, 'pse': pse, 'order': order, 'recent_change':recent_change, 'total_value': total_value, 'client':client,
                   'contact': contact, 'company': company, 'latest_stock': latest_stock, 'subsector': subsector, 'total_value': total_value,
                   'change_in_points': change_in_points, 'lot_size': lot_size,
                   'tick_size': tick_size, 'open_price':open_price, 'high_price':high_price, 'low_price':low_price, 'close_price':close_price, 'last_price':last_price, 'change':change, 'percent_change':percent_change, 'indicator':indicator })


@login_required(login_url='login')
def portfolio(request):

    fetch_stocks()

    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    client = get_object_or_404(Client, user=request.user)

    alerts = client.alert_set.filter(seen=0)

    for alert in alerts:
        alert.seen = 1
        alert.save()


    pse = Index.objects.get(security_symbol="PSE")
    values = client.order_set.values('stock__symbol').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    contact = ContactForm();

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}

    for item in sold:
        company = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company] = item

    portfolio = {}
    total_stock_value = 0

    for item in bought:
        company = Company.objects.get(symbol=item['stock__symbol'])
        if company in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company]['units']
            item['price'] = item['price'] - sold_stocks[company]['price']
            available_stocks = client.order_set.filter(method='B',stock=company).exclude(
                status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).order_by('id')
            number_of_stocks_sold = sold_stocks[company]['units']

            #filter remaining stock
            last_stock_price = 0
            last_stock_units = 0
            units_remaining = 0

            for this_stock in available_stocks:
                if number_of_stocks_sold >= this_stock.units:
                    available_stocks = available_stocks.exclude(id=this_stock.id)
                number_of_stocks_sold = number_of_stocks_sold - this_stock.units
                if(number_of_stocks_sold <= 0):
                    last_stock_price = this_stock.price
                    last_stock_units = this_stock.units
                    units_remaining = number_of_stocks_sold*-1
                    available_stocks = available_stocks.exclude(id=this_stock.id)
                    break

            last_price_per_unit = (last_stock_price/last_stock_units)
            sum_price = available_stocks.aggregate(sum_price=Sum('price'))['sum_price']

            if sum_price:
                sum_price = float(sum_price) + float(last_price_per_unit*units_remaining)
            else:
                sum_price = float(last_price_per_unit*units_remaining)

            item['price'] = sum_price



        if item['units'] > 0:

            item['stockprice'] = company.stockprice_set.order_by('-date_details').first()
            
            latest_stock_item = company.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company] = item


            lastclose=float(latest_stock_item.last_traded_price)/((float(latest_stock_item.percentage_change_close)/100)+1)
            item['change']=float(latest_stock_item.last_traded_price)-lastclose


    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    order_set = client.order_set.order_by('-id')

    wallet_set = client.transaction_set.order_by('-id')[:10]

    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company] = item

        

    for item in portfolio:
        company = Company.objects.get(symbol=item.symbol)
        
        if company in today_stocks:

            stock_item = company.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company]['units'] - today_stocks[company]['units']
            today_ex_portfolio_price = portfolio[company]['price'] - today_stocks[company]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company.stockprice_set.last()

            stock_change = portfolio[company]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change


    pending_transactions = Order.objects.all().filter(client__user=request.user, status__in=['Pen'])

    # localization
    folder = 'client/en/'  # default EN

    if client.language == 'ja':
        folder = 'client/ja/'
    elif client.language == 'kr':
        folder = 'client/kr/'

    return render(request, str(folder + 'portfolio.html'),
                  {'alerts':alerts, 'marketstatus': marketstatus, 'client': client, 'pse': pse, 'portfolio': portfolio, 'order_set': order_set,
                   'total_stock_value': total_stock_value, 'pending_stocks': pending_stocks,
                   'today_transactions': today_transactions, 'pending_transactions': pending_transactions,
                   'contact': contact, 'wallet_set': wallet_set, 'recent_change':recent_change})



@login_required(login_url='login')
def orders(request):
    if request.method == 'GET':
        client = get_object_or_404(Client, user=request.user)

        contact = ContactForm();

        order_set = client.order_set.order_by('-id')

        today_transactions = Order.objects.all().filter(client__user=request.user, last_updated__date=date.today())

        # localization
        folder = 'client/en/'  # default EN

        if client.language == 'ja':
            folder = 'client/ja/'
        elif client.language == 'kr':
            folder = 'client/kr/'

        return render(request, str(folder + 'orders.html'),
                      {'client': client, 'order_set': order_set, 'today_transactions': today_transactions,
                       'contact': contact})
    elif request.method == 'POST':
        form = ContactForm(request.POST)
        user = request.user
        if form.is_valid():
            data = form.cleaned_data
            subject = data['subject']
            content = data['content']

            # Email the profile with the
            # contact information
            template = get_template('contact_template.txt')

            context = Context({
                'content': content,
            })

            email_body = template.render(context)

            if (user.email is not None):
                EmailMessage(
                    subject='tesst',
                    body=email_body,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[user.email]
                ).send()

            EmailMessage(
                subject=subject,
                body=email_body,
                from_email=settings.EMAIL_HOST_USER,
                to=settings.ROI_RECIPIENTS,
                headers={'Reply-To': user.email}
            ).send()

            return HttpResponseRedirect('/')


@login_required(login_url='login')
def account(request):
    marketstatus = SystemOption.objects.filter(name='marketstatus').first()

    client = get_object_or_404(Client, user=request.user)
    pse = Index.objects.get(security_symbol="PSE")

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    sold_stocks = {}

    for item in sold:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        sold_stocks[company_item] = item

    portfolio = {}
    total_stock_value = 0

    for item in bought:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        if company_item in sold_stocks:
            item['units'] = item['units'] - sold_stocks[company_item]['units']
            item['price'] = item['price'] - sold_stocks[company_item]['price']
        if item['units'] > 0:

            item['stockprice'] = company_item.stockprice_set.order_by('-date_details').first()

            latest_stock_item = company_item.stockprice_set.last()
            total_stock_value = total_stock_value + (item['units'] * latest_stock_item.last_traded_price)
            portfolio[company_item] = item

    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    today_transactions = client.order_set.values('stock__symbol').filter(method='B', status__in=['Exe'],
                                                    last_updated__date=date.today()).annotate(price=Sum('price')).annotate(units=Sum('units')).annotate(charge=Sum('charge'))

    today_stocks = {}

    recent_change = 0

    for item in today_transactions:
        company_item = Company.objects.get(symbol=item['stock__symbol'])
        today_stocks[company_item] = item

        

    for item in portfolio:
        company_item = Company.objects.get(symbol=item.symbol)
        
        if company_item in today_stocks:

            stock_item = company_item.stockprice_set.last()

            today_ex_portfolio_units = portfolio[company_item]['units'] - today_stocks[company_item]['units']
            today_ex_portfolio_price = portfolio[company_item]['price'] - today_stocks[company_item]['price']

            if today_ex_portfolio_units > 0:
                stock_change = today_ex_portfolio_price * stock_item.percentage_change_close/100
                recent_change = recent_change + stock_change
            else:
                today_only_portfolio_price = today_stocks[company_item]['price']

                stock_change = (stock_item.last_traded_price*today_stocks[company_item]['units']) - today_only_portfolio_price
                recent_change = recent_change + stock_change
        else:
            stock_item = company_item.stockprice_set.last()

            stock_change = portfolio[company_item]['units'] * (stock_item.last_traded_price - (stock_item.last_traded_price/((stock_item.percentage_change_close/100)+1)))
            recent_change = recent_change + stock_change

    contact = ContactForm();

    newpassword = request.POST.get("newpassword")
    renewpasssword = request.POST.get("renewpasssword")
    username = request.user.username
    if newpassword == renewpasssword:
        if request.method == 'GET':
            form = ChangePasswordForm()
        else:
            u = User.objects.get(username__exact=username)
            u.set_password(newpassword)
            u.save()
            return HttpResponseRedirect(reverse('client:account'))
    else:
        return HttpResponseRedirect(reverse('client:account'))

    # localization
    folder = 'client/en/'  # default EN

    if client.language == 'ja':
        folder = 'client/ja/'
    elif client.language == 'kr':
        folder = 'client/kr/'

    return render(request, str(folder + 'account.html'),
                  {'marketstatus': marketstatus, 'client': client, 'pse': pse, 'form': form, 'contact': contact, 'recent_change':recent_change, 'total_stock_value':total_stock_value})