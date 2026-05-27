from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('messaging', '0002_message_is_internal')]
    operations = [
        migrations.AddField(
            model_name='message',
            name='command',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='message',
            name='command_meta',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='thread',
            name='flagged',
            field=models.BooleanField(default=False),
        ),
    ]
