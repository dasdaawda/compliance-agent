from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserRole

class ClientRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    company_name = forms.CharField(required=False, max_length=255)

    class Meta:
        model = User
        fields = ['email', 'company_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            user.username = email
            user.email = email
        user.role = UserRole.CLIENT
        if commit:
            user.save()
        return user