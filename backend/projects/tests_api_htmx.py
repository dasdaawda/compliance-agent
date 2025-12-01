import json
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage

from users.models import User, UserRole
from projects.models import Project, Video, VideoStatus
from ai_pipeline.models import AITrigger, VerificationTask


class APIAuthenticationTests(APITestCase):
    """Test JWT authentication for API."""
    
    def setUp(self):
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
    
    def test_obtain_jwt_token(self):
        """Test obtaining JWT token."""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'client@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_access_api_with_jwt(self):
        """Test accessing API with JWT token."""
        refresh = RefreshToken.for_user(self.client_user)
        access_token = str(refresh.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('project-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_access_api_without_token(self):
        """Test accessing API without token returns 401."""
        url = reverse('project-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProjectAPITests(APITestCase):
    """Test Project API endpoints."""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        self.other_client = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        
        refresh = RefreshToken.for_user(self.client_user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user,
            description='Test description'
        )
    
    def test_list_projects(self):
        """Test listing user's projects."""
        url = reverse('project-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Project')
    
    def test_create_project(self):
        """Test creating a new project."""
        url = reverse('project-list')
        data = {
            'name': 'New Project',
            'description': 'New description'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 2)
        self.assertEqual(response.data['name'], 'New Project')
    
    def test_cannot_see_other_users_projects(self):
        """Test that users can only see their own projects."""
        other_project = Project.objects.create(
            name='Other Project',
            owner=self.other_client
        )
        
        url = reverse('project-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertNotIn('Other Project', [p['name'] for p in response.data['results']])
    
    def test_project_statistics(self):
        """Test project statistics endpoint."""
        url = reverse('project-statistics', args=[self.project.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_videos', response.data)
        self.assertIn('completed', response.data)


class VideoAPITests(APITestCase):
    """Test Video API endpoints."""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT,
            balance_minutes=1000
        )
        
        refresh = RefreshToken.for_user(self.client_user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user
        )
        
        self.video = Video.objects.create(
            project=self.project,
            original_name='test_video.mp4',
            duration=120,
            file_size=1024000,
            status=VideoStatus.COMPLETED
        )
    
    def test_list_videos(self):
        """Test listing user's videos."""
        url = reverse('video-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_filter_videos_by_status(self):
        """Test filtering videos by status."""
        Video.objects.create(
            project=self.project,
            original_name='processing.mp4',
            status=VideoStatus.PROCESSING
        )
        
        url = reverse('video-list') + '?status=PROCESSING'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'PROCESSING')
    
    def test_video_upload_validation_file_size(self):
        """Test video upload file size validation."""
        url = reverse('video-list')
        
        large_file = SimpleUploadedFile(
            "large_video.mp4",
            b"x" * (3 * 1024 * 1024 * 1024),  # 3 GB
            content_type="video/mp4"
        )
        
        data = {
            'project': str(self.project.id),
            'original_name': 'Large Video',
            'video_file': large_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_file', response.data)
    
    def test_video_upload_validation_format(self):
        """Test video upload format validation."""
        url = reverse('video-list')
        
        invalid_file = SimpleUploadedFile(
            "test.txt",
            b"not a video",
            content_type="text/plain"
        )
        
        data = {
            'project': str(self.project.id),
            'original_name': 'Invalid File',
            'video_file': invalid_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PermissionTests(APITestCase):
    """Test role-based permissions."""
    
    def setUp(self):
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
        self.other_client = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user
        )
    
    def test_client_cannot_access_other_client_project(self):
        """Test that client cannot access another client's project."""
        refresh = RefreshToken.for_user(self.other_client)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('project-detail', args=[self.project.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_operator_cannot_create_project(self):
        """Test that operator cannot create projects."""
        refresh = RefreshToken.for_user(self.operator_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('project-list')
        data = {'name': 'Test', 'description': 'Test'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HTMXViewTests(TestCase):
    """Test HTMX views."""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        self.client.login(username='client@test.com', password='testpass123')
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user
        )
    
    def test_dashboard_view(self):
        """Test dashboard view loads correctly."""
        url = reverse('projects:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'client/dashboard.html')
    
    def test_htmx_project_list_partial(self):
        """Test HTMX project list partial."""
        url = reverse('projects:project_list_partial')
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/project_list.html')
        self.assertContains(response, 'Test Project')
    
    def test_htmx_project_create_get(self):
        """Test HTMX project create form GET."""
        url = reverse('projects:project_create_partial')
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/project_form.html')
    
    def test_htmx_project_create_post(self):
        """Test HTMX project create POST."""
        url = reverse('projects:project_create_partial')
        data = {
            'name': 'New HTMX Project',
            'description': 'Created via HTMX'
        }
        response = self.client.post(url, data, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Project.objects.filter(name='New HTMX Project').exists())
        self.assertIn('HX-Trigger', response.headers)
    
    def test_htmx_video_upload_form(self):
        """Test HTMX video upload form."""
        url = reverse('projects:video_upload_partial', args=[self.project.id])
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/video_upload.html')
    
    def test_htmx_request_with_session_auth(self):
        """Test that HTMX requests work with session authentication."""
        url = reverse('projects:project_list_partial')
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)


class SignedURLTests(APITestCase):
    """Test signed URL generation."""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        
        refresh = RefreshToken.for_user(self.client_user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user
        )
        
        self.video = Video.objects.create(
            project=self.project,
            original_name='test_video.mp4',
            video_url='https://cdn.example.com/test_video.mp4',
            status=VideoStatus.COMPLETED
        )
    
    def test_signed_url_endpoint(self):
        """Test signed URL endpoint."""
        url = reverse('video-signed-url', args=[self.video.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('signed_url', response.data)
        self.assertIn('expires_in', response.data)
    
    def test_video_serializer_includes_signed_url(self):
        """Test that video serializer includes signed URL."""
        url = reverse('video-detail', args=[self.video.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('signed_url', response.data)


class HTMXTemplateTests(TestCase):
    """Test HTMX views and templates."""
    
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        self.client.login(username='client@test.com', password='testpass123')
        
        # Set up message storage
        self.session = self.client.session
        self.messages = FallbackStorage(self.session)
        
        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            owner=self.client_user
        )
        
        self.video = Video.objects.create(
            project=self.project,
            original_name='test_video.mp4',
            status=VideoStatus.COMPLETED,
            video_url='https://cdn.example.com/test_video.mp4',
            file_size=1024000,
            duration=120
        )
    
    def test_project_list_template_renders(self):
        """Test that project list template renders with base.html."""
        url = reverse('projects:project_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Compliance Agent')
        self.assertContains(response, 'Мои проекты')
        self.assertContains(response, 'bootstrap')
        self.assertContains(response, 'htmx.org')
    
    def test_project_detail_template_renders(self):
        """Test that project detail template renders with stats."""
        url = reverse('projects:project_detail', args=[self.project.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.name)
        self.assertContains(response, 'Всего видео')
        self.assertContains(response, 'Завершено')
        self.assertContains(response, 'Загрузить видео')
    
    def test_video_detail_template_renders(self):
        """Test that video detail template renders with status badge."""
        url = reverse('projects:video_detail', args=[self.video.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.video.original_name)
        self.assertContains(response, 'Готово')  # VideoStatus.COMPLETED display
        self.assertContains(response, 'Просмотреть отчет')
    
    def test_video_upload_template_renders(self):
        """Test that video upload template renders."""
        url = reverse('projects:video_upload', args=[self.project.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Загрузить видео')
        self.assertContains(response, self.project.name)
        self.assertContains(response, 'Форма загрузки видео')
    
    def test_htmx_project_list_partial(self):
        """Test HTMX partial for project list."""
        url = reverse('projects:project_list_partial')
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.name)
    
    def test_htmx_video_list_partial(self):
        """Test HTMX partial for video list."""
        url = reverse('projects:video_list_partial', args=[self.project.id])
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.video.original_name)
        self.assertContains(response, 'badge bg-success')  # Status badge
    
    def test_htmx_video_upload_partial_success(self):
        """Test HTMX partial video upload with success triggers."""
        video_file = SimpleUploadedFile(
            "test_video.mp4", 
            b"fake video content", 
            content_type="video/mp4"
        )
        
        url = reverse('projects:video_upload_partial', args=[self.project.id])
        response = self.client.post(
            url,
            {'original_name': 'Test Upload', 'video_file': video_file},
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('HX-Trigger', response)
        trigger_data = json.loads(response['HX-Trigger'])
        self.assertIn('videosUpdated', trigger_data)
        self.assertIn('messagesUpdated', trigger_data)
        self.assertEqual(trigger_data['videosUpdated']['projectId'], str(self.project.id))
    
    def test_htmx_video_upload_partial_validation_error(self):
        """Test HTMX partial video upload with validation errors."""
        url = reverse('projects:video_upload_partial', args=[self.project.id])
        response = self.client.post(
            url,
            {'original_name': 'Test Upload'},  # Missing video_file
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'video_file')
        self.assertNotIn('HX-Trigger', response)
    
    def test_htmx_project_create_partial_success(self):
        """Test HTMX partial project creation with success triggers."""
        url = reverse('projects:project_create_partial')
        response = self.client.post(
            url,
            {'name': 'New Project', 'description': 'New Description'},
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('HX-Trigger', response)
        trigger_data = json.loads(response['HX-Trigger'])
        self.assertIn('projectCreated', trigger_data)
        self.assertIn('messagesUpdated', trigger_data)
    
    def test_htmx_messages_partial(self):
        """Test HTMX messages partial."""
        # Add a message to the session
        self.session['_messages'] = []
        self.messages.add('Test message', 'success')
        self.session.save()
        
        url = reverse('projects:messages_partial')
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test message')
        self.assertContains(response, 'alert-success')
    
    def test_responsive_video_list_partial(self):
        """Test that video list partial has responsive design."""
        url = reverse('projects:video_list_partial', args=[self.project.id])
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'd-none d-md-table-cell')  # Responsive columns
        self.assertContains(response, 'd-none d-lg-table-cell')  # More responsive columns
        self.assertContains(response, 'btn-group')  # Action buttons group
        self.assertContains(response, 'video-player-' + str(self.video.id))  # Video player row
    
    def test_video_status_badges_use_choices(self):
        """Test that video status badges use VideoStatus choices."""
        # Create videos with different statuses
        for status in [VideoStatus.UPLOADED, VideoStatus.PROCESSING, VideoStatus.VERIFICATION, VideoStatus.FAILED]:
            Video.objects.create(
                project=self.project,
                original_name=f'video_{status}.mp4',
                status=status
            )
        
        url = reverse('projects:video_list_partial', args=[self.project.id])
        response = self.client.get(url, HTTP_HX_REQUEST='true')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'badge bg-secondary')  # UPLOADED
        self.assertContains(response, 'badge bg-warning')    # PROCESSING
        self.assertContains(response, 'badge bg-info')       # VERIFICATION
        self.assertContains(response, 'badge bg-success')    # COMPLETED
        self.assertContains(response, 'badge bg-danger')     # FAILED
