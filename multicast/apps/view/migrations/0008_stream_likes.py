# Generated by Django 4.0.4 on 2022-07-10 16:33

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('view', '0007_stream_editors_choice'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='likes',
            field=models.ManyToManyField(related_name='liked_streams', to=settings.AUTH_USER_MODEL),
        ),
    ]