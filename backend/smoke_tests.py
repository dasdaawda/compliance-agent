"""
Smoke tests for API and HTMX implementation.
Run with: python manage.py test smoke_tests
"""
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User, UserRole
from projects.models import Project


class SmokeTests(TestCase):
    """Quick smoke tests to verify basic functionality."""
    
    def setUp(self):
        """Set up test users."""
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        self.operator_user = User.objects.create_user(
            username='operator@test.com',
            email='operator@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
    
    def test_jwt_authentication_works(self):
        """Smoke test: JWT authentication."""
        client = APIClient()
        
        # Obtain token
        url = reverse('token_obtain_pair')
        response = client.post(url, {
            'username': 'client@test.com',
            'password': 'testpass123'
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        
        # Use token
        token = response.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = reverse('project-list')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_api_returns_json(self):
        """Smoke test: API returns JSON."""
        refresh = RefreshToken.for_user(self.client_user)
        token = str(refresh.access_token)
        
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = reverse('video-list')
        response = client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_htmx_request_works(self):
        """Smoke test: HTMX request with session auth."""
        client = Client()
        client.login(username='client@test.com', password='testpass123')
        
        url = reverse('projects:project_list_partial')
        response = client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
    
    def test_permission_enforcement_client(self):
        """Smoke test: Client permissions enforced."""
        refresh = RefreshToken.for_user(self.client_user)
        token = str(refresh.access_token)
        
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Client can access projects
        url = reverse('project-list')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Client cannot access operator tasks
        url = '/api/verification-tasks/'
        response = client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_permission_enforcement_operator(self):
        """Smoke test: Operator permissions enforced."""
        refresh = RefreshToken.for_user(self.operator_user)
        token = str(refresh.access_token)
        
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Operator can access tasks
        url = '/api/verification-tasks/'
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Operator cannot create projects
        url = reverse('project-list')
        response = client.post(url, {'name': 'Test'}, format='json')
        self.assertEqual(response.status_code, 403)
    
    def test_project_owner_isolation(self):
        """Smoke test: Projects are isolated by owner."""
        # Create project for client
        project = Project.objects.create(
            name='Client Project',
            owner=self.client_user
        )
        
        # Client can see their project
        refresh = RefreshToken.for_user(self.client_user)
        token = str(refresh.access_token)
        
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = reverse('project-detail', args=[project.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Other client cannot see it
        other_client = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        
        refresh = RefreshToken.for_user(other_client)
        token = str(refresh.access_token)
        
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = reverse('project-detail', args=[project.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_api_docs_accessible(self):
        """Smoke test: API documentation is accessible."""
        client = Client()
        
        # Schema endpoint
        url = reverse('schema')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Swagger UI
        url = reverse('swagger-ui')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_redirects_properly(self):
        """Smoke test: Root redirect works."""
        client = Client()
        
        # Unauthenticated redirect
        response = client.get('/')
        self.assertEqual(response.status_code, 302)
        
        # Authenticated access
        client.login(username='client@test.com', password='testpass123')
        response = client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response.url)


if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_app.settings')
    django.setup()
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['smoke_tests'])
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
    else:
        print("\n✅ All smoke tests passed!")
