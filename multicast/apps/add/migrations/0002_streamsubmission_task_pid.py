# Generated by Django 3.2.8 on 2021-11-19 18:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('add', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='streamsubmission',
            name='task_pid',
            field=models.CharField(default='none', max_length=50),
            preserve_default=False,
        ),
    ]