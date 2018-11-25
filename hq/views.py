from django.shortcuts import render
from client.models import *
from .forms import *
from django.core.urlresolvers import reverse
from django.core.mail import EmailMessage
from django.template import Context
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect



# from datetime import datetime, date, timedelta
import datetime
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from pseparser.models import Company
from django.shortcuts import get_object_or_404

from roi import settings

import requests as requests

import json

import csv

from django.db.models import Sum, Case, When, F, FloatField



# Create your views here.
@login_required(login_url='login')
def all(request):
    orders = Order.objects.all().order_by('id')
    return render(request, 'hq/orders.html', {'orders': orders})


# Create your views here.
@login_required(login_url='login')
def alldate(request):
    orders = Order.objects.all().order_by('id')
    return render(request, 'hq/orders.html', {'orders': orders})


@login_required(login_url='login')
def orders(request):
    orders = Order.objects.all().order_by('id').exclude(status__in=['Exe', 'Can'])
    return render(request, 'hq/orders.html', {'orders': orders})

@login_required(login_url='login')
def orderstracker(request):
    orders = Order.objects.all().order_by('id').exclude(status__in=['Exe', 'Can'])


    for order in orders:
        current = order.stock.stockprice_set.order_by('-date_details').first()
        orderprice = order.price/order.units

        order.lastprice = current.last_traded_price

        order.percent = ((orderprice/current.last_traded_price) - 1)*100

        order.red = 1-(abs(order.percent)/5)
        order.yellow = abs(order.percent)*25


    return render(request, 'hq/orders_tracker.html', {'orders': orders})

@login_required(login_url='login')
def clients(request):
    clients = Client.objects.all().order_by('id')

    return render(request, 'hq/clients.html', {'clients': clients})

@login_required(login_url='login')
def filter(request, order_filter):
    orders = Order.objects.filter(execution_type=order_filter)
    return render(request, 'hq/orders_filter.html', {'orders': orders})

@login_required(login_url='login')
def today(request):
    orders = Order.objects.filter(status__in=['Exe'], last_updated__date=datetime.date.today())
    return render(request, 'hq/orders_today.html', {'orders': orders})


@login_required(login_url='login')
def status(request, order_status):
    orders = Order.objects.filter(status=order_status)
    return render(request, 'hq/orders_filter.html', {'orders': orders})

@login_required(login_url='login')
def detail(request, order_id):
    admin = request.user
    order = Order.objects.get(id=order_id)
    old_price = order.price
    old_charge =  order.charge

    if request.method == 'POST':
        form = AdminOrderForm(request.POST, instance=order)
        print(form)
        if form.is_valid():
            print('old price', old_price)
            print('new price', form.cleaned_data['price'])
            price_difference = old_price - form.cleaned_data['price']
            charge_difference = old_charge - form.cleaned_data['charge']
            client = order.client
            if order.status == 'Exe':
                if order.method == 'B':
                    client.wallet = client.wallet + price_difference + charge_difference
                else:
                    client.wallet = client.wallet + (form.cleaned_data['price'] + form.cleaned_data['charge'])

            if order.status == 'Can':
                if order.method == 'B':
                    client.wallet = client.wallet + old_price + form.cleaned_data['charge']
                    
                    template = get_template('cancel-template.txt')
                    context = Context({
                        'content': "content",
                    })
                    email_body = template.render(context)
                    EmailMessage(
                        subject='Order Cancelled',
                        body= email_body,
                        from_email=settings.EMAIL_HOST_USER,
                        to=settings.EDIT_RECIPIENTS
                    ).send()
                else:
                    client.wallet = client.wallet + form.cleaned_data['charge']
                    
                    template = get_template('cancel-template.txt')
                    context = Context({
                        'content': 'content',
                    })
                    email_body = template.render(context)
                    EmailMessage(
                        subject='Order Cancelled',
                        body= email_body,
                        from_email=settings.EMAIL_HOST_USER,
                        to=settings.EDIT_RECIPIENTS
                    ).send()

            client.wallet = client.wallet 

            client.save()
            form.save()
            #return HttpResponseRedirect(reverse('hq:detail'))
            return HttpResponseRedirect(reverse('hq:detail', args=(order_id,)))

    else:
        form = AdminOrderForm(instance=order)

    return render(request, 'hq/order_detail.html', {'form':form, 'order': order, 'admin': admin})

@login_required(login_url='login')
def order_split(request, order_id):
    admin = request.user
    order = Order.objects.get(id=order_id)
    units = order.units
    price = order.price

    if request.method == 'POST':
        form = OrderSplit(request.POST)
        if form.is_valid():
            first_split = form.cleaned_data['split1']
            second_split = form.cleaned_data['split2']

            priceperunit = price/units

            if units == first_split+second_split:

                Order.objects.create(
                    client = order.client,
                    stock = order.stock,
                    method = order.method,
                    order_type = order.order_type,
                    execution_type = order.execution_type,
                    price = priceperunit*first_split,
                    upper_limit = order.upper_limit,
                    units = first_split,
                    expiration = order.expiration,
                    status = order.status,
                    charge = order.charge,
                    others = order.others
                )

                Order.objects.create(
                    client = order.client,
                    stock = order.stock,
                    method = order.method,
                    order_type = order.order_type,
                    execution_type = order.execution_type,
                    price = priceperunit*second_split,
                    upper_limit = order.upper_limit,
                    units = second_split,
                    expiration = order.expiration,
                    status = order.status,
                    charge = order.charge,
                    others = order.others
                )

                order.status = 'Can'
                order.save()

            return HttpResponseRedirect(reverse('hq:order_list'))
    else:
        form = OrderSplit()

    return render(request, 'hq/order_split.html', {'form':form, 'order': order, 'admin': admin})

 # if request.method == 'POST':
 #        order_form = AddPortfolio(request.POST)
 #        if order_form.is_valid():
 #            order = Order(client=client, stock=company)
 #            order_form = AddPortfolio(request.POST, instance=order)
 #            order_form.save()


 #            return HttpResponseRedirect(reverse('hq:add_portfolio', args=(client_id,symbol,)))

 #    else:
 #        order_form = AddPortfolio()



 #            return HttpResponseRedirect(reverse('hq:detail', args=(order_id,)))


 #    return render()


@login_required(login_url='login')
def client(request, client_id):
    admin = request.user

    client = Client.objects.get(id=client_id)

    cid = client_id

    bought = client.order_set.values('stock__symbol').filter(method='B').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units'))
    sold = client.order_set.values('stock__symbol').filter(method='S').exclude(
        status__in=['Pen', 'Par', 'Rev', 'Rej', 'Can']).annotate(price=Sum('price')).annotate(units=Sum('units'))

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
            available_stocks = client.order_set.filter(method='B',stock__company=company).exclude(
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

    pending_stocks = client.order_set.filter(status__in=['Pen', 'Rev'], method='B').aggregate(price=Sum('price'))[
        'price']
    if not pending_stocks:
        pending_stocks = 0

    order_set = client.order_set.order_by('-id')

    today_transactions = Order.objects.all().filter(client__user=request.user, method='B', status__in=['Exe'],
                                                    last_updated__date=datetime.date.today())

    pending_transactions = Order.objects.all().filter(client__user=request.user, status__in=['Pen'])

    if request.method == 'POST':

        current = client.wallet

        form = AddWallet(request.POST, instance=client)
        print(form)
        if form.is_valid():
            newwallet = form.cleaned_data['wallet']

            client.wallet = current + newwallet

            client.save()

            if newwallet > 0:
                Transaction.objects.create(
                    client=client,
                    order_type='A',
                    amount=newwallet,
                    note='Add Fund'
                )
            else:
                Transaction.objects.create(
                    client=client,
                    order_type='W',
                    amount=newwallet,
                    note='Withdraw'
                )

            return HttpResponseRedirect(reverse('hq:client', args=(client_id,)))

    else:
        form = AddWallet(instance=client)


    return render(request, 'hq/client_detail.html', {'client': client, 'form':form, 'admin': admin, 'portfolio': portfolio, 'order_set': order_set,'pending_stocks': pending_stocks,
                   'today_transactions': today_transactions, 'pending_transactions': pending_transactions})

@login_required(login_url='login')
def create_client(request):

    if request.method == 'POST':
        user_form = UserCreationForm(request.POST)
        client_form = ClientCreateForm(request.POST)
        if user_form.is_valid() and client_form.is_valid:
            u = user_form.save()

            new_client = Client(user=u)
            client_form = ClientCreateForm(request.POST, instance=new_client)
            c = client_form.save()

            return HttpResponseRedirect(reverse('hq:order_list'))

    else:
        user_form = UserCreationForm()
        client_form = ClientCreateForm()

    return render(request, 'hq/create_client.html', {'user_form': user_form, 'client_form': client_form})





@login_required(login_url='login')
def add_portfolio(request, client_id, symbol):
    company = get_object_or_404(Company, symbol=symbol)
    client = Client.objects.get(id=client_id)

    if request.method == 'POST':
        order_form = AddPortfolio(request.POST)
        if order_form.is_valid():
            order = Order(client=client, stock=company)
            order_form = AddPortfolio(request.POST, instance=order)
            order_form.save()


            return HttpResponseRedirect(reverse('hq:add_portfolio', args=(client_id,symbol,)))

    else:
        order_form = AddPortfolio()

    return render(request, 'hq/add_portfolio.html', {'order_form': order_form, 'client': client, 'company': company, 'client_id': client_id, 'symbol': symbol})



@login_required(login_url='login')
def endofday(request):

    MO = Order.objects.filter(execution_type__in=['MO'], status__in=['Pen'])

    for item in MO:
        item.status = 'Can'

        item.save()

    GTD = Order.objects.filter(expiration__in=['D'], status__in=['Pen'])

    for item in GTD:
        item.status = 'Can'

        item.save()


    return HttpResponse(str('Cancelled ')+ str(len(MO)) + str(' Market Orders and ') + str(len(GTD))+ str(' GTD.'))


@csrf_exempt
def analytics(request):

    # http://tradepro-mft.com/hq/analytics/?from=11/00/2017&to=12/20/2017&client=40

    from_date = request.GET.get('from')
    to_date = request.GET.get('to')

    client_id = request.GET.get('client')

    if client_id is not None:
        client = Client.objects.get(id=client_id)
    else:
        client = None

    from_datetime = datetime.datetime.strptime(from_date, "%m/%d/%Y").date()
    to_datetime = datetime.datetime.strptime(to_date, "%m/%d/%Y").date()

    if client is not None:
        orders = Order.objects.filter(date_created__range=(from_datetime, to_datetime), client=client)

        executions = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), client=client, status__in=['Exe'])
        cancellations = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), client=client, status__in=['Can'])


        pending = Order.objects.filter(status__in=['Pen'], client=client)
        queued = Order.objects.filter(status__in=['Par'], client=client)
        processing = Order.objects.filter(status__in=['Rev'], client=client)

    else:
        orders = Order.objects.filter(date_created__range=(from_datetime, to_datetime))
        executions = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), status__in=['Exe'])
        cancellations = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), status__in=['Can'])


        pending = Order.objects.filter(status__in=['Pen'])
        queued = Order.objects.filter(status__in=['Par'])
        processing = Order.objects.filter(status__in=['Rev'])

    

    
 

    data = {
        # "orders": order_array
        "exectued": len(executions),
        "postedorders": len(orders),
        "processing": len(processing),
        "queued": len(queued),
        "pendingorders": len(processing),
        "cancellations": len(cancellations)


        # "remaining_pending": remaining_pending
        # "processing": remaining_processing
        # "processed": processed
    }
    

    return JsonResponse(data, content_type='text/plain; charset=UTF-8', safe=False)



@csrf_exempt
def analyticscsv(request):

    # http://tradepro-mft.com/hq/analytics/?from=11/00/2017&to=12/20/2017&client=40

    from_date = request.GET.get('from')
    to_date = request.GET.get('to')

    client_id = request.GET.get('client')

    if client_id is not None:
        client = Client.objects.get(id=client_id)
    else:
        client = None

    from_datetime = datetime.datetime.strptime(from_date, "%m/%d/%Y").date()
    to_datetime = datetime.datetime.strptime(to_date, "%m/%d/%Y").date()

    if client is not None:
        orders = Order.objects.filter(date_created__range=(from_datetime, to_datetime), client=client)

        executions = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), client=client, status__in=['Exe'])
        cancellations = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), client=client, status__in=['Can'])


        pending = Order.objects.filter(status__in=['Pen'], client=client)
        queued = Order.objects.filter(status__in=['Par'], client=client)
        processing = Order.objects.filter(status__in=['Rev'], client=client)

    else:
        orders = Order.objects.filter(date_created__range=(from_datetime, to_datetime))
        executions = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), status__in=['Exe'])
        cancellations = Order.objects.filter(last_updated__range=(from_datetime, to_datetime), status__in=['Can'])


        pending = Order.objects.filter(status__in=['Pen'])
        queued = Order.objects.filter(status__in=['Par'])
        processing = Order.objects.filter(status__in=['Rev'])


    # data = {
    #     # "orders": order_array
    #     "exectued": len(executions),
    #     "postedorders": len(orders),
    #     "processing": len(processing),
    #     "queued": len(queued),
    #     "pendingorders": len(processing),
    #     "cancellations": len(cancellations)


    #     # "remaining_pending": remaining_pending
    #     # "processing": remaining_processing
    #     # "processed": processed
    # }

    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="csvanalytics.csv"'

    writer = csv.writer(response)

    for item in orders:
        writer.writerow([item.client, item.stock, item.method, item.execution_type, item.price, item.units, item.status])


    return response




@csrf_exempt
def orders_api(request):

    order_array = []

    message_array = request.body
    message_array = json.loads(message_array)

    symbol = message_array['symbol']
    number = message_array['number']
    page = message_array['page']

    if symbol is None:
        orders = Order.objects.filter(stock=company)
    else:
        company = Company.objects.filter(symbol=symbol)
        orders = Order.objects.filter(stock=company)




    for item in orders:
        order_data = {
            "id":item.id
        }

        order_array.append(order_data)


    data = {
        "orders": order_array
    }

    return JsonResponse(data, content_type='text/plain; charset=UTF-8', safe=False)



@csrf_exempt
def notifications(request):

    notifications = AdminNotification.objects.filter(seen=0)

    array = []

    for notification in notifications:

        data = {
            "id": notification.id,
            "order_id": notification.order,
            "message": notification.message,
        }

        array.append(data)

    jsonarray = {'array': array}
    

    return JsonResponse(jsonarray, content_type='text/plain; charset=UTF-8', safe=False)


@csrf_exempt
def dismiss_notifications(request):

    notif_id = request.GET.get('id')

    notifications = AdminNotification.objects.filter(id=notif_id).first()

    notifications.seen = 1

    notifications.save()

    return HttpResponse('success')


@csrf_exempt
def change_market_status(request):
    newstatus = request.GET.get('status')

    status = SystemOption.objects.filter(name="marketstatus").first()

    status.description = newstatus

    status.save()

    return HttpResponse(str('changed to' + newstatus))