# Généré par Django 6.0.3 le 2026-05-18 à 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_visiteur_motif_archivage'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='is_archived',
            field=models.BooleanField(default=False, verbose_name='Est archivé'),
        ),
    ]
