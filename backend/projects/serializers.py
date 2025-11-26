import hashlib
from rest_framework import serializers
from django.conf import settings
from projects.models import Project, Video, VideoStatus
from users.serializers import UserProfileSerializer
from storage.b2_utils import get_b2_utils


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model."""
    owner = UserProfileSerializer(read_only=True)
    videos_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'owner', 'description', 'created_at', 'updated_at', 'videos_count']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def get_videos_count(self, obj):
        """Return count of videos in the project."""
        return obj.videos.count()
    
    def validate_name(self, value):
        """Validate project name uniqueness for the owner."""
        user = self.context['request'].user
        if self.instance:
            if Project.objects.filter(owner=user, name=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("You already have a project with this name.")
        else:
            if Project.objects.filter(owner=user, name=value).exists():
                raise serializers.ValidationError("You already have a project with this name.")
        return value
    
    def create(self, validated_data):
        """Create project with current user as owner."""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class VideoSerializer(serializers.ModelSerializer):
    """Serializer for Video model."""
    project_name = serializers.CharField(source='project.name', read_only=True)
    signed_url = serializers.SerializerMethodField()
    has_risks = serializers.ReadOnlyField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'project', 'project_name', 'original_name',
            'duration', 'file_size', 'status', 'status_message',
            'signed_url', 'has_risks', 'ai_report', 'processed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'duration', 'file_size', 'status', 'status_message',
            'ai_report', 'processed_at', 'created_at', 'updated_at'
        ]
    
    def get_signed_url(self, obj):
        """Generate signed URL for video streaming."""
        if not obj.video_url:
            return None
        
        try:
            b2_utils = get_b2_utils()
            b2_path = obj.video_url.split('/')[-1] if '/' in obj.video_url else obj.video_url
            signed_url = b2_utils.generate_signed_url(b2_path, expiration=3600)
            return signed_url
        except Exception as e:
            return None
    
    def validate_project(self, value):
        """Ensure user owns the project."""
        user = self.context['request'].user
        if value.owner != user:
            raise serializers.ValidationError("You can only upload videos to your own projects.")
        return value


class VideoUploadSerializer(serializers.ModelSerializer):
    """Serializer for video upload with validation."""
    video_file = serializers.FileField(write_only=True)
    checksum = serializers.CharField(required=False, write_only=True)
    
    class Meta:
        model = Video
        fields = ['id', 'project', 'original_name', 'video_file', 'checksum', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']
    
    def validate_video_file(self, value):
        """Validate video file size and format."""
        max_size = getattr(settings, 'MAX_VIDEO_FILE_SIZE', 2147483648)
        allowed_formats = getattr(settings, 'ALLOWED_VIDEO_FORMATS', ['mp4', 'avi', 'mov', 'mkv', 'webm'])
        
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Video file size exceeds maximum allowed size of {max_size / (1024**3):.2f} GB."
            )
        
        file_ext = value.name.split('.')[-1].lower() if '.' in value.name else ''
        if file_ext not in allowed_formats:
            raise serializers.ValidationError(
                f"Video format '{file_ext}' is not allowed. Allowed formats: {', '.join(allowed_formats)}."
            )
        
        return value
    
    def validate_project(self, value):
        """Ensure user owns the project."""
        user = self.context['request'].user
        if value.owner != user:
            raise serializers.ValidationError("You can only upload videos to your own projects.")
        return value
    
    def validate(self, attrs):
        """Additional cross-field validation."""
        video_file = attrs.get('video_file')
        checksum = attrs.get('checksum')
        
        if video_file and not checksum:
            file_content = video_file.read()
            video_file.seek(0)
            checksum = hashlib.sha256(file_content).hexdigest()
            attrs['checksum'] = checksum
        
        if checksum:
            existing_video = Video.objects.filter(
                project=attrs['project']
            ).exclude(
                status=VideoStatus.FAILED
            ).first()
            
            if existing_video:
                existing_file = existing_video.video_file
                if existing_file:
                    existing_content = existing_file.read()
                    existing_file.seek(0)
                    existing_checksum = hashlib.sha256(existing_content).hexdigest()
                    
                    if existing_checksum == checksum:
                        raise serializers.ValidationError(
                            "This video has already been uploaded to this project."
                        )
        
        return attrs
    
    def create(self, validated_data):
        """Create video instance with uploaded file."""
        checksum = validated_data.pop('checksum', None)
        video_file = validated_data.pop('video_file')
        
        video = Video(**validated_data)
        video.video_file = video_file
        video.file_size = video_file.size
        video.status = VideoStatus.UPLOADED
        video.save()
        
        return video


class VideoDetailSerializer(VideoSerializer):
    """Detailed video serializer with AI report."""
    project_details = ProjectSerializer(source='project', read_only=True)
    
    class Meta(VideoSerializer.Meta):
        fields = VideoSerializer.Meta.fields + ['project_details']
