# Generated by Django 3.0.6 on 2020-10-20 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0007_stream_downvote'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='udp_port',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
