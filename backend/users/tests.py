from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.test import Client

from users.forms import ClientRegistrationForm
from users.models import UserRole

User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }

    def test_create_user_with_email(self):
        """Test creating user with email successfully"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.role, UserRole.CLIENT)

    def test_create_user_email_normalized(self):
        """Test email is normalized"""
        email = 'test@EXAMPLE.COM'
        user = User.objects.create_user(
            email=email,
            password='testpass123'
        )
        self.assertEqual(user.email, email.lower())
        self.assertEqual(user.username, email.lower())

    def test_create_user_with_company_name(self):
        """Test creating user with company name"""
        user = User.objects.create_user(
            email='company@example.com',
            password='testpass123',
            company_name='Test Company'
        )
        self.assertEqual(user.company_name, 'Test Company')

    def test_user_roles(self):
        """Test user role properties"""
        client = User.objects.create_user(
            email='client@example.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        operator = User.objects.create_user(
            email='operator@example.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        admin = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role=UserRole.ADMIN
        )

        self.assertTrue(client.is_client)
        self.assertFalse(client.is_operator)
        self.assertFalse(client.is_admin)

        self.assertFalse(operator.is_client)
        self.assertTrue(operator.is_operator)
        self.assertFalse(operator.is_admin)

        self.assertFalse(admin.is_client)
        self.assertFalse(admin.is_operator)
        self.assertTrue(admin.is_admin)

    def test_has_sufficient_balance(self):
        """Test balance checking method"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            balance_minutes=100
        )
        self.assertTrue(user.has_sufficient_balance(50))
        self.assertTrue(user.has_sufficient_balance(100))
        self.assertFalse(user.has_sufficient_balance(150))

    def test_user_str_representation(self):
        """Test string representation of user"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user), 'test@example.com')

    def test_unique_email_constraint(self):
        """Test unique email constraint"""
        User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='test@example.com',
                password='testpass456'
            )

    def test_user_save_method_syncs_username(self):
        """Test that save method syncs username with email"""
        user = User(
            email='test@example.com',
            password='testpass123'
        )
        user.save()
        self.assertEqual(user.username, 'test@example.com')
        self.assertEqual(user.email, 'test@example.com')


class ClientRegistrationFormTest(TestCase):
    def test_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            'email': 'test@example.com',
            'company_name': 'Test Company',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = ClientRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_email_validation(self):
        """Test email validation in form"""
        # Create existing user
        User.objects.create_user(
            email='existing@example.com',
            password='testpass123'
        )

        # Try to register with same email
        form_data = {
            'email': 'existing@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = ClientRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_email_normalization(self):
        """Test email normalization in form"""
        form_data = {
            'email': 'TEST@EXAMPLE.COM',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = ClientRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'test@example.com')

    def test_form_sets_client_role(self):
        """Test that form sets client role"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = ClientRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, UserRole.CLIENT)


class UserViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_client_registration_view_get(self):
        """Test GET request to registration view"""
        response = self.client.get(reverse('users:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_client_registration_view_post_valid(self):
        """Test POST request with valid data"""
        form_data = {
            'email': 'newuser@example.com',
            'company_name': 'New Company',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        response = self.client.post(reverse('users:register'), data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        
        # Check user was created
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.company_name, 'New Company')
        self.assertEqual(user.role, UserRole.CLIENT)

    def test_client_registration_view_post_invalid(self):
        """Test POST request with invalid data"""
        form_data = {
            'email': 'invalid-email',
            'password1': '123',
            'password2': '456'
        }
        response = self.client.post(reverse('users:register'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='invalid-email').exists())


class UserMixinsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            email='client@example.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        self.operator_user = User.objects.create_user(
            email='operator@example.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role=UserRole.ADMIN
        )

    def test_client_access_mixin_anonymous_denied(self):
        """Test that anonymous users are denied"""
        response = self.client.get(reverse('projects:project_list'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_client_access_mixin_client_allowed(self):
        """Test that client users are allowed"""
        self.client.login(email='client@example.com', password='testpass123')
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 200)

    def test_operator_login(self):
        """Test operator can login"""
        self.client.login(email='operator@example.com', password='testpass123')
        response = self.client.get(reverse('operators:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_login(self):
        """Test admin can login"""
        self.client.login(email='admin@example.com', password='testpass123')
        response = self.client.get(reverse('admins:dashboard'))
        self.assertEqual(response.status_code, 200)