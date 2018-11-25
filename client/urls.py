from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^account/$', views.account, name='account'),
    url(r'^watchlist/$', views.watchlist, name='watchlist'),
    url(r'^orders/$', views.orders, name='orders'),
    url(r'^trade/$', views.portfolio, name='portfolio'),
    url(r'^trade/(?P<order_id>[0-9]+)/$', views.edit_order, name='edit_order'),
    # url(r'^test/$', views.test, name='test'),
    url(r'^(?P<symbol>\w+)/$', views.stock, name='stock'),
    url(r'^(?P<symbol>\w+)/buy/$', views.buy, name='buy'),
    url(r'^(?P<symbol>\w+)/sell/$', views.sell, name='sell'),
]