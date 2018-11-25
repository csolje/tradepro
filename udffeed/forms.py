from django import forms

class FileUploadForm(forms.Form):
    # TODO: use subclassing

    symbol = forms.CharField(label="Symbol", required=False)
    file = forms.FileField(label="File", required=False)


class XMLUploadForm(forms.Form):

	datefield = forms.CharField(label="Date", required=False)
	file = forms.FileField(label="File", required=False)