from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from projects.models import Project, Video, VideoStatus
from projects.serializers import (
    ProjectSerializer, VideoSerializer, VideoUploadSerializer, VideoDetailSerializer
)
from users.permissions import IsClient, IsProjectOwner
from storage.b2_utils import get_b2_utils


class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for Project model."""
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsClient | IsProjectOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return projects owned by the current user."""
        return Project.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        """Create project with current user as owner."""
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def videos(self, request, pk=None):
        """Get all videos for a project."""
        project = self.get_object()
        videos = project.videos.all()
        serializer = VideoSerializer(videos, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get project statistics."""
        project = self.get_object()
        videos = project.videos.all()
        
        stats = {
            'total_videos': videos.count(),
            'uploaded': videos.filter(status=VideoStatus.UPLOADED).count(),
            'processing': videos.filter(status=VideoStatus.PROCESSING).count(),
            'verification': videos.filter(status=VideoStatus.VERIFICATION).count(),
            'completed': videos.filter(status=VideoStatus.COMPLETED).count(),
            'failed': videos.filter(status=VideoStatus.FAILED).count(),
            'total_duration': sum(v.duration for v in videos),
            'total_size': sum(v.file_size for v in videos),
        }
        
        return Response(stats)


class VideoViewSet(viewsets.ModelViewSet):
    """ViewSet for Video model."""
    permission_classes = [IsAuthenticated, IsClient | IsProjectOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'project']
    search_fields = ['original_name']
    ordering_fields = ['created_at', 'updated_at', 'duration', 'file_size']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return videos for projects owned by the current user."""
        return Video.objects.filter(project__owner=self.request.user).select_related('project')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return VideoUploadSerializer
        elif self.action == 'retrieve':
            return VideoDetailSerializer
        return VideoSerializer
    
    def perform_create(self, serializer):
        """Create video and trigger AI pipeline."""
        video = serializer.save()
        
        from ai_pipeline.celery_tasks import run_full_pipeline
        run_full_pipeline.delay(str(video.id))
    
    @action(detail=True, methods=['get'])
    def signed_url(self, request, pk=None):
        """Get signed URL for video streaming."""
        video = self.get_object()
        
        if not video.video_url:
            return Response(
                {'error': 'Video URL not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            b2_utils = get_b2_utils()
            b2_path = video.video_url.split('/')[-1] if '/' in video.video_url else video.video_url
            signed_url = b2_utils.generate_signed_url(b2_path, expiration=3600)
            
            return Response({
                'signed_url': signed_url,
                'expires_in': 3600
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to generate signed URL: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """Get AI report for video."""
        video = self.get_object()
        
        if not video.ai_report:
            return Response(
                {'error': 'AI report not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(video.ai_report)
    
    @action(detail=True, methods=['post'])
    def retry_processing(self, request, pk=None):
        """Retry processing for failed video."""
        video = self.get_object()
        
        if video.status != VideoStatus.FAILED:
            return Response(
                {'error': 'Only failed videos can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        video.status = VideoStatus.UPLOADED
        video.status_message = ''
        video.save()
        
        from ai_pipeline.celery_tasks import run_full_pipeline
        run_full_pipeline.delay(str(video.id))
        
        return Response({'message': 'Video processing restarted'})
