# Généré par Django 6.0.3 le 2026-05-18 à 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_service_is_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentprofile',
            name='two_factor_enabled',
            field=models.BooleanField(default=False, verbose_name='2FA activé'),
        ),
        migrations.AddField(
            model_name='agentprofile',
            name='two_factor_secret',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Secret 2FA'),
        ),
    ]
