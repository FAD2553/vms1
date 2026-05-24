# Généré par Django 6.0.3 le 2026-05-18 à 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_visite_motif'),
    ]

    operations = [
        migrations.AddField(
            model_name='visiteur',
            name='motif_archivage',
            field=models.TextField(blank=True, null=True, verbose_name="Motif de l'archivage"),
        ),
    ]
