from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientportalconfig',
            name='portal_theme',
            field=models.CharField(
                choices=[('default', 'Default'), ('infinity', 'Infinity'), ('minimal', 'Minimal')],
                default='default',
                max_length=20,
            ),
        ),
    ]
