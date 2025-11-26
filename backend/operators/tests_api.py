from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User, UserRole
from projects.models import Project, Video, VideoStatus
from ai_pipeline.models import AITrigger, VerificationTask
from operators.models import OperatorLabel


class VerificationTaskAPITests(APITestCase):
    """Test VerificationTask API endpoints."""
    
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='operator@test.com',
            email='operator@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        
        refresh = RefreshToken.for_user(self.operator_user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user
        )
        
        self.video = Video.objects.create(
            project=self.project,
            original_name='test_video.mp4',
            status=VideoStatus.VERIFICATION
        )
        
        self.task = VerificationTask.objects.create(
            video=self.video,
            status=VerificationTask.Status.PENDING
        )
    
    def test_operator_can_list_pending_tasks(self):
        """Test operator can list pending tasks."""
        url = '/api/verification-tasks/pending/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_operator_can_assign_task(self):
        """Test operator can assign task to themselves."""
        url = f'/api/verification-tasks/{self.task.id}/assign/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.operator, self.operator_user)
        self.assertEqual(self.task.status, VerificationTask.Status.IN_PROGRESS)
    
    def test_operator_can_send_heartbeat(self):
        """Test operator can send heartbeat for assigned task."""
        self.task.assign_to_operator(self.operator_user)
        
        url = f'/api/verification-tasks/{self.task.id}/heartbeat/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_operator_can_complete_task(self):
        """Test operator can complete assigned task."""
        self.task.assign_to_operator(self.operator_user)
        
        url = f'/api/verification-tasks/{self.task.id}/complete/'
        data = {'decision_summary': 'All triggers reviewed'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, VerificationTask.Status.COMPLETED)
        self.assertEqual(self.task.decision_summary, 'All triggers reviewed')
    
    def test_operator_cannot_heartbeat_unassigned_task(self):
        """Test operator cannot send heartbeat for unassigned task."""
        url = f'/api/verification-tasks/{self.task.id}/heartbeat/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_client_cannot_access_verification_tasks(self):
        """Test client cannot access verification tasks."""
        refresh = RefreshToken.for_user(self.client_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = '/api/verification-tasks/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OperatorLabelAPITests(APITestCase):
    """Test OperatorLabel API endpoints."""
    
    def setUp(self):
        self.operator_user = User.objects.create_user(
            username='operator@test.com',
            email='operator@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        
        refresh = RefreshToken.for_user(self.operator_user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user
        )
        
        self.video = Video.objects.create(
            project=self.project,
            original_name='test_video.mp4',
            status=VideoStatus.VERIFICATION
        )
        
        self.trigger = AITrigger.objects.create(
            video=self.video,
            timestamp_sec=10.5,
            trigger_source=AITrigger.TriggerSource.WHISPER_PROFANITY,
            confidence=0.95,
            data={'text': 'test'}
        )
    
    def test_operator_can_create_label(self):
        """Test operator can create label."""
        url = '/api/operator-labels/'
        data = {
            'video': str(self.video.id),
            'ai_trigger': str(self.trigger.id),
            'start_time_sec': 10.5,
            'final_label': OperatorLabel.FinalLabel.OK_FALSE,
            'comment': 'False positive'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(OperatorLabel.objects.filter(
            operator=self.operator_user,
            video=self.video
        ).exists())
    
    def test_operator_can_list_their_labels(self):
        """Test operator can list their own labels."""
        OperatorLabel.objects.create(
            video=self.video,
            operator=self.operator_user,
            ai_trigger=self.trigger,
            start_time_sec=10.5,
            final_label=OperatorLabel.FinalLabel.OK
        )
        
        url = '/api/operator-labels/my_labels/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_label_marks_trigger_as_processed(self):
        """Test that creating label marks trigger as processed."""
        url = '/api/operator-labels/'
        data = {
            'video': str(self.video.id),
            'ai_trigger': str(self.trigger.id),
            'start_time_sec': 10.5,
            'final_label': OperatorLabel.FinalLabel.OK,
            'comment': 'Reviewed'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.trigger.refresh_from_db()
        self.assertEqual(self.trigger.status, 'processed')


class TaskAssignmentWorkflowTests(APITestCase):
    """Test complete task assignment workflow."""
    
    def setUp(self):
        self.operator1 = User.objects.create_user(
            username='operator1@test.com',
            email='operator1@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        self.operator2 = User.objects.create_user(
            username='operator2@test.com',
            email='operator2@test.com',
            password='testpass123',
            role=UserRole.OPERATOR
        )
        self.client_user = User.objects.create_user(
            username='client@test.com',
            email='client@test.com',
            password='testpass123',
            role=UserRole.CLIENT
        )
        
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.client_user
        )
        
        self.video = Video.objects.create(
            project=self.project,
            original_name='test_video.mp4',
            status=VideoStatus.VERIFICATION
        )
        
        self.task = VerificationTask.objects.create(
            video=self.video,
            status=VerificationTask.Status.PENDING
        )
    
    def test_second_operator_cannot_assign_locked_task(self):
        """Test that second operator cannot assign already locked task."""
        self.task.assign_to_operator(self.operator1)
        
        refresh = RefreshToken.for_user(self.operator2)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = f'/api/verification-tasks/{self.task.id}/assign/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_operator_can_release_task(self):
        """Test operator can release assigned task."""
        self.task.assign_to_operator(self.operator1)
        
        refresh = RefreshToken.for_user(self.operator1)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = f'/api/verification-tasks/{self.task.id}/release/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, VerificationTask.Status.PENDING)
        self.assertIsNone(self.task.operator)
