from django import forms

class ProductForm(forms.Form):
    title = forms.CharField(max_length=200)
    slug = forms.SlugField()
    description = forms.CharField(widget=forms.Textarea, required=False)
    price = forms.DecimalField(decimal_places=2, max_digits=10)
    stock = forms.IntegerField(min_value=0)
    image = forms.ImageField(required=False)
    active = forms.BooleanField(required=False)
# flowfinds/forms.py 

class AddressForm(forms.Form):
    recipient_name = forms.CharField(label='Full name', max_length=200)
    phone = forms.CharField(label='Phone number', max_length=20)
    address_line1 = forms.CharField(label='Address line 1', max_length=255)
    address_line2 = forms.CharField(label='Address line 2', max_length=255, required=False)
    city = forms.CharField(max_length=100)
    state = forms.CharField(max_length=100)
    pincode = forms.CharField(label='PIN/ZIP', max_length=20)
    country = forms.CharField(max_length=100, initial='India')
    delivery_instructions = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':3}))
