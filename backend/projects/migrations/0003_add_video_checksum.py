from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='checksum',
            field=models.CharField(blank=True, db_index=True, max_length=64, verbose_name='контрольная сумма'),
        ),
    ]
