from django import forms
from client.models import *
from pseparser.models import *
from django.contrib.auth.models import User

class AdminOrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['price', 'units', 'status', 'charge', 'others']

class AddWallet(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['wallet']

class UserCreateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'password', 'email']

class ClientCreateForm(forms.ModelForm):
    class Meta:
        model = Client
        exclude = ['user']

class AddPortfolio(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['method', 'order_type', 'execution_type', 'price', 'upper_limit', 'units', 'expiration', 'status', 'charge', 'others']

class OrderSplit(forms.Form):
    split1 = forms.IntegerField(label="Split1", required=False)
    split2 = forms.IntegerField(label="Split2", required=False)