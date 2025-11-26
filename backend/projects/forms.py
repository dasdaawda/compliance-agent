from django import forms
from .models import Project, Video

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название проекта'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание проекта (необязательно)'
            }),
        }

class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['original_name', 'video_file']
        widgets = {
            'original_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название видео'
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
        }

class VideoURLForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['original_name', 'video_url']
        widgets = {
            'original_name': forms.TextInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

class UnifiedVideoForm(forms.ModelForm):
    """
    Унифицированная форма для загрузки видео — принимает либо файл, либо URL.
    Валидация: требуется ровно одно из полей video_file / video_url.
    """
    class Meta:
        model = Video
        fields = ['original_name', 'video_file', 'video_url']
        widgets = {
            'original_name': forms.TextInput(attrs={'class': 'form-control'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get('video_file')
        url = cleaned.get('video_url')

        if not file and not url:
            raise forms.ValidationError("Требуется указать файл видео или ссылку (video_file или video_url).")
        if file and url:
            raise forms.ValidationError("Укажите только одно: файл видео или ссылку, не оба поля одновременно.")
        return cleaned