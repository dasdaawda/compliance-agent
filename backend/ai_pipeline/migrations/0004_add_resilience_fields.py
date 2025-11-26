# Generated migration for resilience fields

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ai_pipeline', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pipelineexecution',
            name='last_step',
            field=models.CharField(blank=True, max_length=100, verbose_name='последний выполненный шаг'),
        ),
        migrations.AddField(
            model_name='pipelineexecution',
            name='retry_count',
            field=models.IntegerField(default=0, verbose_name='количество повторов'),
        ),
        migrations.AddField(
            model_name='pipelineexecution',
            name='error_trace',
            field=models.JSONField(blank=True, default=list, verbose_name='трасса ошибок'),
        ),
        migrations.CreateModel(
            name='RiskDefinition',
            fields=[
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False, default=uuid.uuid4)),
                ('trigger_source', models.CharField(choices=[('whisper_profanity', 'Whisper - Мат'), ('whisper_brand', 'Whisper - Бренд'), ('falconsai_nsfw', 'Falconsai - NSFW'), ('violence_detector', 'Детектор насилия'), ('yolo_object', 'YOLO - Объект'), ('easyocr_text', 'EasyOCR - Текст')], max_length=50, unique=True, verbose_name='источник триггера')),
                ('name', models.CharField(max_length=255, verbose_name='название риска')),
                ('description', models.TextField(verbose_name='описание')),
                ('risk_level', models.CharField(choices=[('low', 'Низкий'), ('medium', 'Средний'), ('high', 'Высокий')], default='medium', max_length=20, verbose_name='уровень риска')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='дата обновления')),
            ],
            options={
                'verbose_name': 'определение риска',
                'verbose_name_plural': 'определения рисков',
                'ordering': ['trigger_source'],
            },
        ),
    ]
