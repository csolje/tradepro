from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^config/$', views.config, name='config'),
    url(r'^symbols/$', views.symbols, name='symbols'),
    url(r'^history/$', views.history, name='history'),
    url(r'^chart/$', views.chart, name='chart'),
    url(r'^time/$', views.time, name='time'),
    url(r'^pending/$', views.pending, name='pending'),
    url(r'^oldprices/$', views.old, name='old'),
    url(r'^purge/$', views.purge, name='purge'),
    url(r'^newcompany/$', views.newcompany, name='newcompany'),
    url(r'^execute/$', views.execute, name='execute'),
    url(r'^ticker/$', views.ticker, name='ticker'),
    url(r'^brokers/$', views.brokers, name='brokers'),
    url(r'^opening/$', views.opening, name='opening'),
    url(r'^feed/$', views.feed, name='feed'),
    url(r'^psefeed/$', views.psefeed, name='psefeed'),
    url(r'^amiup/$', views.amiup, name='amiup'),
    url(r'^pseconn/$', views.pseconn, name='pseconn'),
]