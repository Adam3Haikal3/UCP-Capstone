from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProfileAddressForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = (
            "street_address",
            "street_address_2",
            "city",
            "state",
            "zip_code",
            "country",
        )
        labels = {
            "street_address": "Street Address",
            "street_address_2": "Apt / Suite / Unit",
            "city": "City",
            "state": "State / Province",
            "zip_code": "ZIP / Postal Code",
            "country": "Country",
        }
        widgets = {
            "street_address": forms.TextInput(attrs={"placeholder": "123 Main St"}),
            "street_address_2": forms.TextInput(attrs={"placeholder": "Apt 4B"}),
            "city": forms.TextInput(attrs={"placeholder": "Columbus"}),
            "state": forms.TextInput(attrs={"placeholder": "OH"}),
            "zip_code": forms.TextInput(attrs={"placeholder": "43210"}),
            "country": forms.TextInput(attrs={"placeholder": "US"}),
        }
