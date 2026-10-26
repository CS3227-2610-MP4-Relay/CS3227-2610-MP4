"""Input validation for sign-in."""

from django import forms


class SignInForm(forms.Form):
    """Reject malformed input, such as NUL characters, before authentication."""

    username = forms.CharField(max_length=150)
    password = forms.CharField(strip=False)
