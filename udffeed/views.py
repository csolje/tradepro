import datetime
import requests as requests

from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render

# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView

from pseparser.models import Company, StockPrice, MarketOrder, OrderBook, LastExecutedOrder, Broker, SystemHealth
from udffeed.service import get_daily_feed, get_minute_feed, get_hour_feed

import json

RETRIEVE_URL = "http://feed.pse-tools.com/feed/history?symbol=%s&resolution=D&from=%d&to=%d"
RETRIEVE_URL2 = "http://phisix-api3.appspot.com/stocks/BDO.2016-12-02.json"



@csrf_exempt
def config(request):
    data = {
        "supported_resolutions": ["5", "15", "30", "60", "D", "1W", "1M"],
        "supports_group_request": False,
        "supports_search": True,
        "supports_marks": False,
        "supports_time": True
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8', safe=False)


@csrf_exempt
def symbol_info(request, group):
    return JsonResponse(status=404)


@csrf_exempt
def symbols(request):
    symbol = request.GET.get('symbol')
    print("getting symbol info for: " + symbol)
    company = Company.objects.filter(symbol=symbol).first()

    data = {
        "name": symbol,
        "exchange-traded": "PSE",
        "exchange-listed": "PSE",
        "timezone": "Asia/Hong_Kong",
        "minmov": 1,
        "minmov2": 0,
        "pricescale": 10000,
        "pointvalue": 1,
        "session": "0930-1530:23456",
        "has_intraday": True,
        "has_no_volume": False,
        "ticker": symbol,
        "description": company.company_name,
        "type": "index",
        "supported_resolutions": ["5", "15", "30", "60", "D", "1W", "1M"],
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8', safe=False)





@csrf_exempt
def history(request):
    symbol = request.GET.get('symbol')
    from_unix = request.GET.get('from')
    to_unix = request.GET.get('to')
    resolution = request.GET.get('resolution')
    print("getting symbol info for: " + symbol)
    company = Company.objects.filter(symbol=symbol).first()
    # response = requests.get("http://www.pse-tools.info/chart/feed/history?symbol=2GO&resolution=D&from=1375023704&to=1476023704")
    # return JsonResponse(response.json(), content_type='text/plain; charset=UTF-8', safe=False)
    from_datetime = datetime.datetime.fromtimestamp(int(from_unix))
    to_datetime = datetime.datetime.fromtimestamp(int(to_unix))

    print("from datetime: " + str(from_datetime))
    print("to datetime: " + str(to_datetime))

    if company is None:
        data = {
            "s": "error"
        }
    else:
        # stock_details = StockDetail.objects.filter(company=company).filter(
        #     date_details__range=(from_datetime, to_datetime))

        if resolution == "D":
            return get_daily_feed(company, from_datetime, to_datetime)
        elif resolution == "W":
            return get_weekly_feed(company, from_datetime, to_datetime)
        elif resolution == "M":
            return get_monthly_feed(company, from_datetime, to_datetime)
        elif resolution == "5" or resolution == 5:
            return get_minute_feed(5, company)
        elif resolution == "15" or resolution == 15:
            return get_minute_feed(15, company)
        elif resolution == "30" or resolution == 30:
            return get_minute_feed(30, company)
        elif resolution == "60" or resolution == 60:
            return get_hour_feed(1, company)



@csrf_exempt
def time(request):
    return HttpResponse(datetime.datetime.now().timestamp())
    # return HttpResponse(1474905600)


@csrf_exempt
def chart(request):
    return render(request, 'feed.html')

@csrf_exempt
def newcompany(request):

    opening_array = request.body
    opening_array = json.loads(opening_array)

    opening_array1 = opening_array['array']
    

    for company in opening_array1:
        symbol = company['symbol']
        symid = company['id']
        pd = company['pd']

        company = Company.objects.filter(symbol=symbol).first()

        if company is not None:
            OrderBook.objects.create(
                company=company,
                price_decimal = pd,
                orderbook_id = symid
            )

    return HttpResponse(str('success'))


@csrf_exempt
def pending(request):
    opening_array = request.body
    opening_array = json.loads(opening_array)

    opening_array1 = opening_array['array']

    lastsequence = MarketOrder.objects.last()

    if lastsequence is None:
        currentdate = 0
        currentnumber = 0
    else:
        currentdate = lastsequence.date_reference
        currentnumber = lastsequence.sequence_number    

    for stock in opening_array1:
        symbol_id = stock['symbol']
        price = stock['price']
        units = stock['units']
        sequencenumber = stock['sequencenumber']
        ordertype = stock['ordertype']

        date = str(sequencenumber)
        date = int(date[:8])
        
        sequence_number = str(sequencenumber)
        sequence_number = int(sequence_number[-10:])

        orderbook = OrderBook.objects.filter(orderbook_id=symbol_id).first()    

        if orderbook is not None:
            if currentdate < date:
                pd = orderbook.price_decimal
                price = float(price)/(10**pd)

                MarketOrder.objects.create(
                    company=orderbook.company,
                    price = price,
                    units = units,
                    date_reference = date,
                    sequence_number = sequence_number,
                    order_type = ordertype
                )
            elif currentdate == date:
                if currentnumber < sequence_number:
                    pd = orderbook.price_decimal
                    price = float(price)/(10**pd)

                    MarketOrder.objects.create(
                        company=orderbook.company,
                        price = price,
                        units = units,
                        date_reference = date,
                        sequence_number = sequence_number,
                        order_type = ordertype
                    )


    return HttpResponse(str('success'))




@csrf_exempt
def purge(request):
    MarketOrder.objects.all().delete()
    return HttpResponse(str('success'))


@csrf_exempt
def old(request):
    opening_array = request.body
    opening_array = json.loads(opening_array)

    opening_array1 = opening_array['array']

    lastsequence = MarketOrder.objects.last()

    if lastsequence is None:
        currentdate = 0
        currentnumber = 0
    else:
        currentdate = lastsequence.date_reference
        currentnumber = lastsequence.sequence_number    

    for stock in opening_array1:
        symbol_id = stock['symbol']
        price = stock['price']
        units = stock['units']
        sequencenumber = stock['sequencenumber']
        ordertype = stock['ordertype']

        date = str(sequencenumber)
        date = int(date[:8])
        
        sequence_number = str(sequencenumber)
        sequence_number = int(sequence_number[-10:])

        orderbook = OrderBook.objects.filter(orderbook_id=symbol_id).first()    

        if orderbook is not None:
            if currentdate < date:
                pd = orderbook.price_decimal
                price = float(price)/(10**pd)

                MarketOrder.objects.create(
                    company=orderbook.company,
                    price = price,
                    units = units,
                    date_reference = date,
                    sequence_number = sequence_number,
                    order_type = ordertype
                )
            elif currentdate == date:
                if currentnumber < sequence_number:
                    pd = orderbook.price_decimal
                    price = float(price)/(10**pd)

                    MarketOrder.objects.create(
                        company=orderbook.company,
                        price = price,
                        units = units,
                        date_reference = date,
                        sequence_number = sequence_number,
                        order_type = ordertype
                    )


    return HttpResponse(str('success'))

@csrf_exempt
def opening(request):
    opening_array = request.body
    opening_array = json.loads(opening_array)

    opening_array1 = opening_array['array']
    

    for stock in opening_array1:
        symbol = stock['symbol']
        price = stock['price']

        company = Company.objects.filter(symbol=symbol).first()

        if company is not None:


            StockPrice.objects.create(
                company=company,
                date_details=datetime.datetime.today(),
                open_price = price,
                low_price = price,
                high_price = price,
                indicator = 'U',
                percentage_change_close = 0,
                total_volume = 0,
                last_traded_price = price
            )

    return HttpResponse(str('Add New Date'))



@csrf_exempt
def execute(request):
    opening_array = request.body
    opening_array = json.loads(opening_array)

    opening_array1 = opening_array['array']
    

    for order in opening_array1:
        sequencenumber = order['orderid']
        units = order['quantity']
        passive_broker = order['passive_broker']
        active_broker = order['active_broker']

        date_reference = str(sequencenumber)
        date_reference = int(date_reference[:8])

        
        sequence_number = str(sequencenumber)
        sequence_number = int(sequence_number[-10:])

        marketorder = MarketOrder.objects.filter(sequence_number=sequence_number, date_reference=date_reference).first()

        if marketorder is not None:

            company = marketorder.company

            price = marketorder.price
            ordertype = marketorder.order_type

            LastExecutedOrder.objects.create(
                company=company,
                price = price,
                units = units,
                order_type = ordertype,
                passive_broker = passive_broker,
                active_broker = active_broker
            )

            marketorder.delete()

        
    return HttpResponse(str('success'))

@csrf_exempt
def brokers(request):

    opening_array1 = [{'brokerid': 100, 'broker': 'UPCCS'}, {'brokerid': 101, 'broker': 'AampA'}, {'brokerid': 102, 'broker': 'Abac'}, {'brokerid': 103, 'broker': 'Accor'}, {'brokerid': 104, 'broker': 'ATdeC'}, {'brokerid': 105, 'broker': 'AllAs'}, {'brokerid': 106, 'broker': 'Alpha'}, {'brokerid': 108, 'broker': 'FiveK'}, {'brokerid': 109, 'broker': 'BASec'}, {'brokerid': 110, 'broker': 'Angpi'}, {'brokerid': 111, 'broker': 'Ansal'}, {'brokerid': 112, 'broker': 'ABCap'}, {'brokerid': 113, 'broker': 'Saran'}, {'brokerid': 115, 'broker': 'SBEq'}, {'brokerid': 116, 'broker': 'AsiaP'}, {'brokerid': 117, 'broker': 'Asiam'}, {'brokerid': 118, 'broker': 'Asias'}, {'brokerid': 119, 'broker': 'Astra'}, {'brokerid': 120, 'broker': 'ATCSe'}, {'brokerid': 121, 'broker': 'Macq'}, {'brokerid': 122, 'broker': 'Belso'}, {'brokerid': 123, 'broker': 'Benja'}, {'brokerid': 124, 'broker': 'BHCh'}, {'brokerid': 125, 'broker': 'JakaS'}, {'brokerid': 126, 'broker': 'BPISe'}, {'brokerid': 128, 'broker': 'Campo'}, {'brokerid': 129, 'broker': 'Since'}, {'brokerid': 130, 'broker': 'Cent'}, {'brokerid': 131, 'broker': 'PCIBS'}, {'brokerid': 132, 'broker': 'Phili'}, {'brokerid': 133, 'broker': 'Citis'}, {'brokerid': 134, 'broker': 'Citic'}, {'brokerid': 135, 'broker': 'Cityt'}, {'brokerid': 136, 'broker': 'Trito'}, {'brokerid': 138, 'broker': 'Phile'}, {'brokerid': 139, 'broker': 'Magn'}, {'brokerid': 140, 'broker': 'IGCSe'}, {'brokerid': 141, 'broker': 'Cualo'}, {'brokerid': 142, 'broker': 'DBPDa'}, {'brokerid': 143, 'broker': 'David'}, {'brokerid': 145, 'broker': 'Diver'}, {'brokerid': 146, 'broker': 'WiseS'}, {'brokerid': 147, 'broker': 'EChua'}, {'brokerid': 148, 'broker': 'Secur'}, {'brokerid': 149, 'broker': 'Eastw'}, {'brokerid': 150, 'broker': 'Easte'}, {'brokerid': 151, 'broker': 'EBCSe'}, {'brokerid': 152, 'broker': 'Rashi'}, {'brokerid': 153, 'broker': 'Equit'}, {'brokerid': 154, 'broker': 'Everg'}, {'brokerid': 155, 'broker': 'FEBSt'}, {'brokerid': 156, 'broker': 'Finve'}, {'brokerid': 157, 'broker': 'First'}, {'brokerid': 158, 'broker': 'Velas'}, {'brokerid': 159, 'broker': 'First'}, {'brokerid': 160, 'broker': 'Fort'}, {'brokerid': 161, 'broker': 'Franc'}, {'brokerid': 162, 'broker': 'FYapS'}, {'brokerid': 165, 'broker': 'GKGoh'}, {'brokerid': 167, 'broker': 'Auror'}, {'brokerid': 168, 'broker': 'Globa'}, {'brokerid': 169, 'broker': 'JSGSe'}, {'brokerid': 170, 'broker': 'Golds'}, {'brokerid': 171, 'broker': 'Guoco'}, {'brokerid': 172, 'broker': 'Guild'}, {'brokerid': 173, 'broker': 'Chris'}, {'brokerid': 174, 'broker': 'HDISe'}, {'brokerid': 175, 'broker': 'HEBen'}, {'brokerid': 176, 'broker': 'ABNAm'}, {'brokerid': 177, 'broker': 'Highl'}, {'brokerid': 178, 'broker': 'HKSec'}, {'brokerid': 179, 'broker': 'IAcke'}, {'brokerid': 180, 'broker': 'IBGim'}, {'brokerid': 181, 'broker': 'Inves'}, {'brokerid': 182, 'broker': 'Imper'}, {'brokerid': 183, 'broker': 'Intra'}, {'brokerid': 184, 'broker': 'DBSVi'}, {'brokerid': 185, 'broker': 'JPMor'}, {'brokerid': 186, 'broker': 'CDIBV'}, {'brokerid': 187, 'broker': 'Asian'}, {'brokerid': 188, 'broker': 'JMBar'}, {'brokerid': 190, 'broker': 'Value'}, {'brokerid': 191, 'broker': 'GoMaA'}, {'brokerid': 192, 'broker': 'Strat'}, {'brokerid': 193, 'broker': 'Larrg'}, {'brokerid': 195, 'broker': 'Liton'}, {'brokerid': 197, 'broker': 'Lopez'}, {'brokerid': 198, 'broker': 'Lucky'}, {'brokerid': 199, 'broker': 'LuysS'}, {'brokerid': 200, 'broker': 'Manda'}, {'brokerid': 200, 'broker': 'Manda'}, {'brokerid': 201, 'broker': 'Maria'}, {'brokerid': 202, 'broker': 'Marin'}, {'brokerid': 203, 'broker': 'MarkS'}, {'brokerid': 204, 'broker': 'DaMar'}, {'brokerid': 205, 'broker': 'Merca'}, {'brokerid': 206, 'broker': 'Merid'}, {'brokerid': 207, 'broker': 'BNPPa'}, {'brokerid': 208, 'broker': 'MDRSe'}, {'brokerid': 209, 'broker': 'Deuts'}, {'brokerid': 210, 'broker': 'Mount'}, {'brokerid': 211, 'broker': 'NewWo'}, {'brokerid': 212, 'broker': 'ETrad'}, {'brokerid': 213, 'broker': 'Nieve'}, {'brokerid': 214, 'broker': 'Nomur'}, {'brokerid': 215, 'broker': 'Optim'}, {'brokerid': 217, 'broker': 'RCBCS'}, {'brokerid': 218, 'broker': 'PanAs'}, {'brokerid': 219, 'broker': 'PapaS'}, {'brokerid': 220, 'broker': 'ATRKi'}, {'brokerid': 221, 'broker': 'BNPPa'}, {'brokerid': 222, 'broker': 'Pierc'}, {'brokerid': 223, 'broker': 'Plati'}, {'brokerid': 224, 'broker': 'PNBSe'}, {'brokerid': 225, 'broker': 'Premi'}, {'brokerid': 226, 'broker': 'Chili'}, {'brokerid': 227, 'broker': 'OCBCS'}, {'brokerid': 228, 'broker': 'Pryce'}, {'brokerid': 229, 'broker': 'Publi'}, {'brokerid': 230, 'broker': 'Quali'}, {'brokerid': 231, 'broker': 'RampL'}, {'brokerid': 232, 'broker': 'Alako'}, {'brokerid': 233, 'broker': 'RCoyi'}, {'brokerid': 234, 'broker': 'PJBPa'}, {'brokerid': 235, 'broker': 'Regin'}, {'brokerid': 236, 'broker': 'RNubl'}, {'brokerid': 237, 'broker': 'AAASo'}, {'brokerid': 238, 'broker': 'RSLim'}, {'brokerid': 239, 'broker': 'RTGam'}, {'brokerid': 240, 'broker': 'SJRox'}, {'brokerid': 241, 'broker': 'Sapph'}, {'brokerid': 242, 'broker': 'Secur'}, {'brokerid': 243, 'broker': 'Fidel'}, {'brokerid': 245, 'broker': 'Orion'}, {'brokerid': 246, 'broker': 'Summi'}, {'brokerid': 247, 'broker': 'Stand'}, {'brokerid': 248, 'broker': 'SunH'}, {'brokerid': 249, 'broker': 'Supre'}, {'brokerid': 250, 'broker': 'Pearl'}, {'brokerid': 251, 'broker': 'Tanse'}, {'brokerid': 252, 'broker': 'TheFi'}, {'brokerid': 253, 'broker': 'Tower'}, {'brokerid': 254, 'broker': 'Trans'}, {'brokerid': 255, 'broker': 'ApexP'}, {'brokerid': 256, 'broker': 'Trend'}, {'brokerid': 257, 'broker': 'TriSt'}, {'brokerid': 258, 'broker': 'SGSec'}, {'brokerid': 259, 'broker': 'UCPBS'}, {'brokerid': 260, 'broker': 'UOBKa'}, {'brokerid': 261, 'broker': 'EIBSe'}, {'brokerid': 263, 'broker': 'Vent'}, {'brokerid': 265, 'broker': 'Jocri'}, {'brokerid': 266, 'broker': 'Vicsa'}, {'brokerid': 267, 'broker': 'First'}, {'brokerid': 268, 'broker': 'HSBCS'}, {'brokerid': 269, 'broker': 'Wealt'}, {'brokerid': 270, 'broker': 'Westl'}, {'brokerid': 271, 'broker': 'KGISe'}, {'brokerid': 272, 'broker': 'Berna'}, {'brokerid': 273, 'broker': 'WongS'}, {'brokerid': 274, 'broker': 'World'}, {'brokerid': 275, 'broker': 'Yaoam'}, {'brokerid': 276, 'broker': 'PhilP'}, {'brokerid': 277, 'broker': 'Yapti'}, {'brokerid': 278, 'broker': 'Yuamp'}, {'brokerid': 279, 'broker': 'BDOSe'}, {'brokerid': 280, 'broker': 'Topwi'}, {'brokerid': 282, 'broker': 'PCCIS'}, {'brokerid': 283, 'broker': 'Eagle'}, {'brokerid': 285, 'broker': 'Golde'}, {'brokerid': 286, 'broker': 'Solar'}, {'brokerid': 287, 'broker': 'Parag'}, {'brokerid': 288, 'broker': 'GDTan'}, {'brokerid': 289, 'broker': 'Grand'}, {'brokerid': 323, 'broker': 'CLSAP'}, {'brokerid': 328, 'broker': 'Thing'}, {'brokerid': 333, 'broker': 'UBSSe'}, {'brokerid': 338, 'broker': 'Phili'}, {'brokerid': 345, 'broker': 'Unica'}, {'brokerid': 368, 'broker': 'Secur'}, {'brokerid': 369, 'broker': 'Activ'}, {'brokerid': 387, 'broker': 'Coher'}, {'brokerid': 388, 'broker': 'Armst'}, {'brokerid': 389, 'broker': 'Kings'}]
    

    for order in opening_array1:
        broker = order['broker']
        broker_id = order['brokerid']

        Broker.objects.create(
            broker=broker,
            broker_id = broker_id,
        )

    return HttpResponse(str('success'))

@csrf_exempt
def pseconn(request):

    conn = request.body
    conn = json.loads(conn)

    conn1 = conn['array']

    psehealth = SystemHealth.objects.filter(name='pse').first()

    for status in conn1:
        psehealth.timestamp = status['timestamp']


    return HttpResponse(str('success'))


@csrf_exempt
def amiup(request):

    psehealth = SystemHealth.objects.filter(name='pse').first()

    data = {
        "name": "PSE",
        "timestamp": psehealth.timestamp
    }

    if psehealth is None:
        data = {}

    array = [data]

    health = {'array': array}

    return JsonResponse(health, content_type='text/plain; charset=UTF-8', safe=False)



@csrf_exempt
def ticker(request):
    lastorders = LastExecutedOrder.objects.order_by('-id')[:24]


    array = []

    for order in lastorders:
        company = order.company
        if order.order_type == "b":
            a_broker = Broker.objects.filter(broker_id=order.passive_broker).first()
            p_broker = Broker.objects.filter(broker_id=order.active_broker).first()
        else:
            p_broker = Broker.objects.filter(broker_id=order.passive_broker).first()
            a_broker = Broker.objects.filter(broker_id=order.active_broker).first()

        datetoday = datetime.date.today()

        stockprice = StockPrice.objects.filter(company=company,date_details=datetoday).first()

        changeclose = stockprice.percentage_change_close


        if a_broker is not None:
            a_broker_name = a_broker.broker
        else:
            a_broker_name = "0"

        if p_broker is not None:
            p_broker_name = p_broker.broker
        else:
            p_broker_name = "0"

        price = order.price

        if price > 4000:
            price = price/10000

        if price > 0.49:
            data = {
                "stock": company.symbol,
                "price": float("{0:.2f}".format(price)),
                "units": int(order.units),
                "abroker": a_broker_name,
                "pbroker": p_broker_name,
                "indicator": stockprice.indicator,
            }

        else:
            data = {
                "stock": company.symbol,
                "price": float("{0:.4f}".format(price)),
                "units": int(order.units),
                "abroker": a_broker_name,
                "pbroker": p_broker_name,
                "indicator": stockprice.indicator,
                "chance": changeclose
            }

        array.append(data)

    tickerfeed = {'array': array}

    return JsonResponse(tickerfeed, content_type='text/plain; charset=UTF-8', safe=False)

    

@csrf_exempt
def feed(request):
    companies = Company.objects.exclude(security_status='S').order_by('symbol')

    array = []
    sym1 = []
    sym2 = []
    sym3 = []
    sym4 = []
    sym5 = []

    for company in companies:
        stockprice = StockPrice.objects.filter(company=company).last()
        if stockprice is not None:
            data = {
                "stock": company.symbol,
                "stock_name": company.security_name
            }
        if len(company.symbol) == 1:
            sym1.append(data)
        if len(company.symbol) == 2:
            sym2.append(data)
        if len(company.symbol) == 3:
            sym3.append(data)
        if len(company.symbol) == 4:
            sym4.append(data)
        if len(company.symbol) == 5:
            sym5.append(data)

        array = sym1 + sym2 + sym3 + sym4 + sym5

    feed = {'array': array}

    return JsonResponse(feed, content_type='text/plain; charset=UTF-8', safe=False)




@csrf_exempt
def psefeed(request):
    message_array = request.body
    message_array = json.loads(message_array)
    message_array = message_array['array']
    
    for message in message_array:
        message_type = message['Type']

        # ADD ORDER
        # {"Type":"A","Timestamp":1000000,"OrderNumber":201703070000000241,"OrderVerb":"B","Quantity":10000,"Orderbook":5050,"Price":228500}
        if message_type == "A":
            ordernumber = message['OrderNumber']
            orderverb = message['OrderVerb']
            quantity = message['Quantity']
            orderbook = message['Orderbook']
            price = message['Price']

            orderbook = OrderBook.objects.filter(orderbook_id=orderbook).first()
            

            if orderbook is not None:
                if ordernumber > 0:

                    date = str(ordernumber)
                    date = int(date[:8])
                    
                    sequence_number = str(ordernumber)
                    sequence_number = int(sequence_number[-10:])

                    company = orderbook.company
                    pd = 4

                    price = float(price)/10000

                    if price > 4000:
                        price = price/10000

                    if orderverb=="B":
                        ordertype = 'b'
                    else:
                        ordertype = 'a'

                    MarketOrder.objects.create(
                        company=company,
                        price = price,
                        units = quantity,
                        date_reference = date,
                        sequence_number = sequence_number,
                        order_type = ordertype
                    )

                # if ordernumber == 0:
                #     company = orderbook.company
                #     pd = orderbook.price_decimal

                #     price = float(price)/float(10**pd)
                #     stockprice_past = StockPrice.objects.filter(company=company).order_by('-date_details')[0]
                #     last_close = float(stockprice_past.last_traded_price)

                #     if price > last_close:
                #         indicator = 'U'
                #     elif price < last_close:
                #         indicator = 'D'
                #     else:
                #         indicator = 'N'

                #     change_close = (price/last_close)-1
                #     change_close = change_close*100


                #     StockPrice.objects.create(
                #         company=company,
                #         date_details=datetime.datetime.today(),
                #         open_price = price,
                #         low_price = price,
                #         high_price = price,
                #         indicator = indicator,
                #         percentage_change_close = change_close,
                #         total_volume = 0,
                #         last_traded_price = price
                #     )


        # EXECUTE ORDER (Aunonymous)
        # {"Type":"E","Timestamp":639000000,"OrderNumber":201703080000000152,"ExecutedQuantity":4000,"MatchNumber":21}
        if message_type == "E":
            ordernumber = message['OrderNumber']
            executedquantity = message['ExecutedQuantity']
            matchnumber = message['MatchNumber']

            date_reference = str(ordernumber)
            date_reference = int(date_reference[:8])

            sequence_number = str(ordernumber)
            sequence_number = int(sequence_number[-10:])

            marketorder = MarketOrder.objects.filter(sequence_number=sequence_number, date_reference=date_reference).first()

            datetoday = datetime.date.today();


            if marketorder is not None:
                company = marketorder.company
                stockpricetoday = StockPrice.objects.filter(company=company, date_details=datetoday).first()

                if stockpricetoday is None:

                    stockprice_yesterday = StockPrice.objects.filter(company=company).order_by('-date_details')[0]

                    oldprice = stockprice_yesterday.last_traded_price
                    price = marketorder.price

                    if price > 4000:
                        price = price/10000

                    units = marketorder.units

                    percent_change = (price/oldprice) - 1

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"

                    # StockPrice.objects.create(
                    #     company=company,
                    #     date_details=datetoday,
                    #     open_price = price,
                    #     low_price = price,
                    #     high_price = price,
                    #     indicator = indicator,
                    #     percentage_change_close = percent_change,
                    #     total_volume = units,
                    #     last_traded_price = price
                    # )

                    ordertype = marketorder.order_type

                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype
                    )

                    marketorder.delete()

                else:
                    oldprice = stockpricetoday.last_traded_price
                    oldpercentage = stockpricetoday.percentage_change_close



                    price = marketorder.price

                    if price > 4000:
                        price = price/10000

                    units = marketorder.units

                    newoldprice = oldprice/(oldpercentage+1)
                    percent_change = price/(newoldprice + 1)

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"

                    stockpricetoday.last_traded_price = price
                    stockpricetoday.indicator = indicator
                    stockpricetoday.percentage_change_close = percent_change
                    stockpricetoday.total_volume = stockpricetoday.total_volume + units

                    previous_low = float(stockpricetoday.low_price)
                    previous_high = float(stockpricetoday.high_price)
                    compare = float(price)

                    if compare < previous_low:
                        stockpricetoday.low_price = price

                    if compare > previous_high:
                        stockpricetoday.previous_high = price

                    # stockpricetoday.save()

                    ordertype = marketorder.order_type
                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype
                    )

                    marketorder.delete()

                # marketorder.delete()

        # EXECUTE ORDER (With Broker IDs)
        # {"Type":"e","Timestamp":639000000,"OrderNumber":201703080000000152,"ExecutedQuantity":4000,"MatchNumber":21,"PassiveBrokerID":"101 ","ActiveBrokerID":"101 "}
        if message_type == "e":
            ordernumber = message['OrderNumber']
            executedquantity = message['ExecutedQuantity']
            matchnumber = message['MatchNumber']
            passivebroker = message['PassiveBrokerID']
            activebroker = message['ActiveBrokerID']

            if passivebroker == "    ":
                passivebroker = 0
            if activebroker == "    ":
                activebroker = 0

            date_reference = str(ordernumber)
            date_reference = int(date_reference[:8])

            sequence_number = str(ordernumber)
            sequence_number = int(sequence_number[-10:])

            marketorder = MarketOrder.objects.filter(sequence_number=sequence_number, date_reference=date_reference).first()

            datetoday = datetime.date.today();


            if marketorder is not None:
                company = marketorder.company
                stockpricetoday = StockPrice.objects.filter(company=company, date_details=datetoday).first()

                if stockpricetoday is None:

                    stockprice_yesterday = StockPrice.objects.filter(company=company).order_by('-date_details')[0]

                    oldprice = stockprice_yesterday.last_traded_price
                    price = marketorder.price

                    if price > 4000:
                        price = price/10000

                    units = marketorder.units

                    percent_change = (price/oldprice) - 1

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"

                    # StockPrice.objects.create(
                    #     company=company,
                    #     date_details=datetoday,
                    #     open_price = price,
                    #     low_price = price,
                    #     high_price = price,
                    #     indicator = indicator,
                    #     percentage_change_close = percent_change,
                    #     total_volume = units,
                    #     last_traded_price = price
                    # )

                    ordertype = marketorder.order_type

                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype,
                        passive_broker = passivebroker,
                        active_broker = activebroker
                    )

                    marketorder.delete()

                else:
                    oldprice = stockpricetoday.last_traded_price
                    oldpercentage = stockpricetoday.percentage_change_close

                    price = marketorder.price

                    if price > 4000:
                        price = price/10000

                    units = marketorder.units

                    newoldprice = oldprice/(oldpercentage+1)
                    percent_change = price/(newoldprice + 1)

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"

                    stockpricetoday.last_traded_price = price
                    stockpricetoday.indicator = indicator
                    stockpricetoday.percentage_change_close = percent_change
                    stockpricetoday.total_volume = stockpricetoday.total_volume + units

                    previous_low = float(stockpricetoday.low_price)
                    previous_high = float(stockpricetoday.high_price)
                    compare = float(price)

                    if compare < previous_low:
                        stockpricetoday.low_price = price

                    if compare > previous_high:
                        stockpricetoday.previous_high = price

                    # stockpricetoday.save()

                    ordertype = marketorder.order_type
                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype,
                        passive_broker = passivebroker,
                        active_broker = activebroker
                    )

                    marketorder.delete()



            # last_close = float(stockprice_yesterday.last_traded_price)

            # if price > last_close:
            #     indicator = 'U'
            # elif price < last_close:
            #     indicator = 'D'
            # else:
            #     indicator = 'N'

            # change_close = ((price/last_close)-1)*100

            # stockpricetoday.open_price = price
            # stockpricetoday.indicator = indicator
            # stockpricetoday.percentage_change_close = change_close
            # stockpricetoday.total_volume = stockpricetoday.total_volume + executedquantity

            # stockpricetoday.save()

            # if marketorder is not None:

            #     company = marketorder.company

            #     price = marketorder.price
            #     ordertype = marketorder.order_type

            #     LastExecutedOrder.objects.create(
            #         company=company,
            #         price = price,
            #         units = executedquantity,
            #         order_type = ordertype,
            #         passive_broker = passivebroker,
            #         active_broker = activebroker
            #     )

            #     marketorder.delete()

        # EXECUTE ORDER (With Price Message and Aunonymous)
        # {"Type":"c","Timestamp":1000000,"OrderNumber":201702230000001700,"ExecutedQuantity":1000,"MatchNumber":1,"Printable":"Y","ExecutionPrice":850000,"PassiveBrokerID":"162 ","ActiveBrokerID":"    "}
        if message_type == "C":
            ordernumber = message['OrderNumber']
            executedquantity = message['ExecutedQuantity']
            matchnumber = message['MatchNumber']
            executionprice = message['ExecutionPrice']

            date_reference = str(ordernumber)
            date_reference = int(date_reference[:8])

            sequence_number = str(ordernumber)
            sequence_number = int(sequence_number[-10:])

            marketorder = MarketOrder.objects.filter(sequence_number=sequence_number, date_reference=date_reference).first()

            if marketorder is not None:
                company = marketorder.company
                stockpricetoday = StockPrice.objects.filter(company=company, date_details=datetoday).first()

                if stockpricetoday is None:

                    stockprice_yesterday = StockPrice.objects.filter(company=company).order_by('-date_details')[0]

                    oldprice = stockprice_yesterday.last_traded_price
                    units = marketorder.units

                    percent_change = (price/oldprice) - 1

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"

                    # StockPrice.objects.create(
                    #     company=company,
                    #     date_details=datetoday,
                    #     open_price = price,
                    #     low_price = price,
                    #     high_price = price,
                    #     indicator = indicator,
                    #     percentage_change_close = percent_change,
                    #     total_volume = units,
                    #     last_traded_price = price
                    # )

                    ordertype = marketorder.order_type

                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype,
                        passive_broker = passivebroker,
                        active_broker = activebroker
                    )

                    marketorder.delete()

                else:
                    oldprice = stockpricetoday.last_traded_price
                    oldpercentage = stockpricetoday.percentage_change_close

                    price = marketorder.price
                    units = marketorder.units

                    newoldprice = oldprice/(oldpercentage+1)
                    percent_change = price/(newoldprice + 1)

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"


                    stockpricetoday.last_traded_price = price
                    stockpricetoday.indicator = indicator
                    stockpricetoday.percentage_change_close = percent_change
                    stockpricetoday.total_volume = stockpricetoday.total_volume + units

                    previous_low = float(stockpricetoday.low_price)
                    previous_high = float(stockpricetoday.high_price)
                    compare = float(price)

                    if compare < previous_low:
                        stockpricetoday.low_price = price

                    if compare > previous_high:
                        stockpricetoday.previous_high = price

                    # stockpricetoday.save()

                    ordertype = marketorder.order_type
                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype,
                        passive_broker = passivebroker,
                        active_broker = activebroker
                    )

                    marketorder.delete()
                # company = marketorder.company
                # ordertype = marketorder.order_type
                # orderbook = OrderBook.objects.filter(company=company).first()

                # pd = 4
                # price = float(executionprice)/10000

                # stockpricetoday = StockPrice.objects.filter(company=company).order_by('-date_details')[0]
                # stockprice_yesterday = StockPrice.objects.filter(company=company).order_by('-date_details')[1]

                # last_close = float(stockprice_yesterday.last_traded_price)


                # change_close = ((price/last_close)-1)*100

                # if change_close > 0:
                #     indicator="U"
                # elif change_close < 0:
                #     indicator="D"
                # else:
                #     indicator="N"


                # stockpricetoday.open_price = price
                # stockpricetoday.indicator = indicator
                # stockpricetoday.percentage_change_close = change_close
                # stockpricetoday.total_volume = stockpricetoday.total_volume + executedquantity

                # stockpricetoday.save()

                # LastExecutedOrder.objects.create(
                #     company=company,
                #     price = price,
                #     units = executedquantity,
                #     order_type = ordertype,
                #     passive_broker = '0',
                #     active_broker = '0'
                # )

                # marketorder.delete()

        # EXECUTE ORDER (With Price Message)
        if message_type == "c":
            ordernumber = message['OrderNumber']
            executedquantity = message['ExecutedQuantity']
            matchnumber = message['MatchNumber']
            executionprice = message['ExecutionPrice']
            passivebroker = message['PassiveBrokerID']
            activebroker = message['ActiveBrokerID']

            price = executionprice/10000

            if passivebroker == "    ":
                passivebroker = 0
            if activebroker == "    ":
                activebroker = 0

            date_reference = str(ordernumber)
            date_reference = int(date_reference[:8])

            sequence_number = str(ordernumber)
            sequence_number = int(sequence_number[-10:])

            marketorder = MarketOrder.objects.filter(sequence_number=sequence_number, date_reference=date_reference).first()

            datetoday = datetime.date.today();


            if marketorder is not None:
                company = marketorder.company
                stockpricetoday = StockPrice.objects.filter(company=company, date_details=datetoday).first()

                if stockpricetoday is None:

                    stockprice_yesterday = StockPrice.objects.filter(company=company).order_by('-date_details')[0]

                    oldprice = stockprice_yesterday.last_traded_price
                    units = marketorder.units

                    percent_change = (price/oldprice) - 1

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"

                    # StockPrice.objects.create(
                    #     company=company,
                    #     date_details=datetoday,
                    #     open_price = price,
                    #     low_price = price,
                    #     high_price = price,
                    #     indicator = indicator,
                    #     percentage_change_close = percent_change,
                    #     total_volume = units,
                    #     last_traded_price = price
                    # )

                    ordertype = marketorder.order_type

                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype,
                        passive_broker = passivebroker,
                        active_broker = activebroker
                    )

                    marketorder.delete()

                else:
                    oldprice = stockpricetoday.last_traded_price
                    oldpercentage = stockpricetoday.percentage_change_close

                    price = marketorder.price
                    units = marketorder.units

                    newoldprice = oldprice/(oldpercentage+1)
                    percent_change = price/(newoldprice + 1)

                    if percent_change > 0:
                        indicator="U"
                    elif percent_change < 0:
                        indicator="D"
                    else:
                        indicator="N"


                    stockpricetoday.last_traded_price = price
                    stockpricetoday.indicator = indicator
                    stockpricetoday.percentage_change_close = percent_change
                    stockpricetoday.total_volume = stockpricetoday.total_volume + units

                    previous_low = float(stockpricetoday.low_price)
                    previous_high = float(stockpricetoday.high_price)
                    compare = float(price)

                    if compare < previous_low:
                        stockpricetoday.low_price = price

                    if compare > previous_high:
                        stockpricetoday.previous_high = price

                    # stockpricetoday.save()

                    ordertype = marketorder.order_type
                    LastExecutedOrder.objects.create(
                        company=company,
                        price = price,
                        units = executedquantity,
                        order_type = ordertype,
                        passive_broker = passivebroker,
                        active_broker = activebroker
                    )

                    marketorder.delete()


                # stockpricetoday.save()

                # LastExecutedOrder.objects.create(
                #     company=company,
                #     price = price,
                #     units = executedquantity,
                #     order_type = ordertype,
                #     passive_broker = passivebroker,
                #     active_broker = activebroker
                # )

                # marketorder.delete()

        # DELETE ORDER
        # {"Type":"D","Timestamp":347000000,"OrderNumber":201703080000000021}
        if message_type == "D":
            ordernumber = message['OrderNumber']
            date_reference = str(ordernumber)
            date_reference = int(date_reference[:8])

            sequence_number = str(ordernumber)
            sequence_number = int(sequence_number[-10:])

            marketorder = MarketOrder.objects.filter(sequence_number=sequence_number, date_reference=date_reference).first()
            if marketorder is not None:
                marketorder.delete()

        # REVISE ORDER
        # {"Type":"U","Timestamp":384000000,"OriginalOrderNumber":201703080000000023,"NewOrderNumber":201703080000000024,"Quantity":1000,"Price":28000}
        if message_type == "U":
            originalordernumber = message['OriginalOrderNumber']
            newordernumber = message['NewOrderNumber']
            quantity = message['Quantity']
            price = message['Price']

            price = price/10000

            old_date_reference = str(originalordernumber)
            old_date_reference = int(old_date_reference[:8])

            old_sequence_number = str(originalordernumber)
            old_sequence_number = int(old_sequence_number[-10:])

            marketorder = MarketOrder.objects.filter(sequence_number=old_sequence_number, date_reference=old_date_reference).first()

            if marketorder is not None:
                date_reference = str(newordernumber)
                date_reference = int(date_reference[:8])

                sequence_number = str(newordernumber)
                sequence_number = int(sequence_number[-10:])

                marketorder.date_reference = date_reference
                marketorder.sequence_number = sequence_number
                marketorder.price = price
                marketorder.units = quantity

                marketorder.save()


        # CLOSE PRICE
        # {"Type":"p","Timestamp":169000000,"ExecutedQuantity":999,"Orderbook":5216,"Printable":"Y","ExecutionPrice":16000,"MatchNumber":6,"TradeIndicator":"C","BuyBrokerId":"323 ","SellBrokerId":"323 "}
        # if message_type == "P":
        


        # sequencenumber = order['orderid']
        # units = order['quantity']
        # passive_broker = order['passive_broker']
        # active_broker = order['active_broker']

        # date_reference = str(sequencenumber)
        # date_reference = int(date_reference[:8])

        
        # sequence_number = str(sequencenumber)
        # sequence_number = int(sequence_number[-10:])

        # marketorder = MarketOrder.objects.filter(sequence_number=sequence_number, date_reference=date_reference).first()

        # if marketorder is not None:

        #     company = marketorder.company
        #     price = marketorder.price
        #     ordertype = marketorder.order_type

        #     LastExecutedOrder.objects.create(
        #         company=company,
        #         price = price,
        #         units = units,
        #         order_type = ordertype,
        #         passive_broker = passive_broker,
        #         active_broker = active_broker
        #     )

        #     marketorder.delete()

        
    return HttpResponse(str('success'))




