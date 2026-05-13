"""
Django Forms (non-DRF) used by the web dashboard views.
These are the HTML form counterparts to the DRF serializers.

Place: web/forms/auth_forms.py
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class APIKeyCreateForm(forms.Form):
    label = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class":       "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm "
                           "focus:outline-none focus:ring-2 focus:ring-indigo-500",
            "placeholder": "e.g. Production, CI/CD, Mobile App",
        }),
        help_text="A memorable name so you can identify this key later.",
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            "type":  "datetime-local",
            "class": "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm",
        }),
        help_text="Leave blank for a non-expiring key.",
    )


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ["full_name"]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm",
            }),
        }


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"}),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"}),
        validators=[validate_password],
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={"class": "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_password") != cleaned.get("new_password2"):
            raise forms.ValidationError("New passwords do not match.")
        return cleaned


class TOTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6, min_length=6,
        widget=forms.TextInput(attrs={
            "class":         "w-40 border border-gray-300 rounded-lg px-3 py-2 text-sm "
                             "text-center tracking-widest font-mono",
            "autocomplete":  "one-time-code",
            "inputmode":     "numeric",
            "placeholder":   "000000",
        }),
    )