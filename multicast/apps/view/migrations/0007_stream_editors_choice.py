# Generated by Django 4.0.4 on 2022-07-06 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('view', '0006_stream_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='editors_choice',
            field=models.BooleanField(default=False),
        ),
    ]
