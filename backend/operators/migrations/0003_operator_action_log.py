# Generated migration for OperatorActionLog

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('ai_pipeline', '0005_add_operator_task_lifecycle'),
        ('operators', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OperatorActionLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action_type', models.CharField(choices=[('assigned_task', 'Назначен задачу'), ('heartbeat', 'Обновил активность'), ('completed_task', 'Завершил задачу'), ('released_task', 'Освободил задачу'), ('processed_trigger', 'Обработал триггер'), ('resumed_task', 'Возобновил задачу')], max_length=20, verbose_name='тип действия')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='детали')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='время действия')),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='action_logs', to='users.user', verbose_name='оператор')),
                ('task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='action_logs', to='ai_pipeline.verificationtask', verbose_name='задача')),
                ('trigger', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='action_logs', to='ai_pipeline.aitrigger', verbose_name='триггер')),
            ],
            options={
                'verbose_name': 'лог действия оператора',
                'verbose_name_plural': 'логи действий операторов',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='operatoractionlog',
            index=models.Index(fields=['operator', '-timestamp'], name='operators_operator_action__timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='operatoractionlog',
            index=models.Index(fields=['task', '-timestamp'], name='operators_task__timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='operatoractionlog',
            index=models.Index(fields=['action_type', '-timestamp'], name='operators_action_type__timestamp_idx'),
        ),
    ]