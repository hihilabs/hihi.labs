import uuid
from django.db import migrations, models


def _populate_tokens(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    for client in Client.objects.filter(portal_token__isnull=True):
        client.portal_token = uuid.uuid4()
        client.save(update_fields=['portal_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0005_alter_client_hosted_domain_alter_client_id_and_more'),
    ]

    operations = [
        # 1. Add column without unique so SQLite can copy existing rows
        migrations.AddField(
            model_name='client',
            name='portal_token',
            field=models.UUIDField(
                null=True,
                editable=False,
                help_text='Token for tokenized client portal access URL.',
            ),
        ),
        # 2. Assign a distinct UUID to every existing row
        migrations.RunPython(_populate_tokens, migrations.RunPython.noop),
        # 3. Now enforce unique + set the Python-level default
        migrations.AlterField(
            model_name='client',
            name='portal_token',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                help_text='Token for tokenized client portal access URL.',
            ),
        ),
    ]
