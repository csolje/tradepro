from django import forms
from .models import *
from pseparser.models import *

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['method', 'client', 'stock', 'order_type', 'execution_type', 'price', 'upper_limit', 'units', 'expiration', 'others', 'charge']

class EditOrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_type', 'execution_type', 'price', 'upper_limit', 'units', 'status', 'others', 'charge']

class AddToWatchlistForm(forms.Form):
    add = forms.IntegerField()

class ChangePasswordForm(forms.Form):
	newpassword= forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)), label=("New Password"))
	renewpasssword=forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30)), label=("Retype New Password"))
		
class ContactForm(forms.Form):
    subject = forms.CharField(required=True)
    content = forms.CharField(
        required=True,
        widget=forms.Textarea
    )