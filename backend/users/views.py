from django.contrib.auth import login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import ClientRegistrationForm
from .models import User

def client_registration(request):
    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена!')
            return redirect('projects:project_list')
    else:
        form = ClientRegistrationForm()
    
    return render(request, 'users/registration.html', {'form': form})

class ClientAccessMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        # защититься от анонимных пользователей
        if not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_admin", False):
            return True
        if hasattr(self, 'get_object'):
            try:
                obj = self.get_object()
                if hasattr(obj, 'user'):
                    return obj.user == user
                elif hasattr(obj, 'owner'):
                    return obj.owner == user
            except Exception:
                return False
        return getattr(user, "is_client", False)


class OperatorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return getattr(user, "is_authenticated", False) and getattr(user, "is_operator", False)


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return getattr(user, "is_authenticated", False) and getattr(user, "is_admin", False)