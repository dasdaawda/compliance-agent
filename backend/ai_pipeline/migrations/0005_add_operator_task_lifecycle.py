# Generated migration for operator workspace revamp

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('projects', '0001_initial'),
        ('ai_pipeline', '0004_add_resilience_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='verificationtask',
            name='expires_at',
            field=models.DateTimeField(blank=True, help_text='Время, когда блокировка задачи истекает', null=True, verbose_name='истекает в'),
        ),
        migrations.AddField(
            model_name='verificationtask',
            name='last_heartbeat',
            field=models.DateTimeField(blank=True, help_text='Последнее обновление активности оператора', null=True, verbose_name='последний heartbeat'),
        ),
        migrations.AddField(
            model_name='verificationtask',
            name='decision_summary',
            field=models.TextField(blank=True, help_text='Итоговое описание принятых решений', verbose_name='суммарное решение'),
        ),
    ]