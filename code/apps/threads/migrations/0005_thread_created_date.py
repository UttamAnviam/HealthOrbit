# Generated by Django 5.1.2 on 2024-10-25 08:06

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('threads', '0004_thread_thread_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='thread',
            name='created_date',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
    ]
