# Generated by Django 3.0.6 on 2021-04-23 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0009_auto_20210423_0211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='group',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='stream',
            name='source',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='stream',
            name='udp_port',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
