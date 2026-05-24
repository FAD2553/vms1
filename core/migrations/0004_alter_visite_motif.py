# Généré par Django 6.0.3 le 2026-05-18 à 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_remove_visite_porte_visite_porte_entree_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visite',
            name='motif',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Motif de la visite'),
        ),
    ]
