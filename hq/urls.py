from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^orders/$', views.orders, name='order_list'),
    url(r'^orders/all$', views.all, name='order_all'),
    url(r'^orders/tracker$', views.orderstracker, name='orders_tracker'),
    url(r'^orders/filter/(?P<order_filter>\w+)/$', views.filter, name='order_type'),
    url(r'^orders/status/(?P<order_status>\w+)/$', views.status, name='order_status'),
    url(r'^orders/(?P<order_id>[0-9]+)/$', views.detail, name='detail'),
    url(r'^orders/today/$', views.today, name='today'),
    url(r'^clients/$', views.clients, name='clients'),
    url(r'^clients/client/(?P<client_id>[0-9]+)/$', views.client, name='client'),
    url(r'^clients/create$', views.create_client, name='create_client'),
    url(r'^add/(?P<client_id>[0-9]+)/(?P<symbol>\w+)$', views.add_portfolio, name='add_portfolio'),
    url(r'^ordersapi/$', views.orders_api, name='orders_api'),
    url(r'^analytics/$', views.analytics, name='analytics'),
    url(r'^analyticscsv/$', views.analyticscsv, name='analyticscsv'),
    url(r'^endofday/$', views.endofday, name='endofday'),
    url(r'^split/(?P<order_id>[0-9]+)/$', views.order_split, name='order_split'),
    url(r'^notifications/$', views.notifications, name='notifications'),
    url(r'^dismissnotifications/$', views.dismiss_notifications, name='dismiss_notifications'),
    url(r'^change_market_status/$', views.change_market_status, name='change_market_status'),
]