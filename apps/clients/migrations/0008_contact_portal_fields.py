import uuid
from django.db import migrations, models


def _populate_tokens(apps, schema_editor):
    Contact = apps.get_model('clients', 'Contact')
    for contact in Contact.objects.filter(portal_token__isnull=True):
        contact.portal_token = uuid.uuid4()
        contact.save(update_fields=['portal_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0007_client_portal_linked_clients'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='portal_token',
            field=models.UUIDField(
                null=True,
                editable=False,
                help_text="Token for this contact's individual portal access URL.",
            ),
        ),
        migrations.RunPython(_populate_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='contact',
            name='portal_token',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                help_text="Token for this contact's individual portal access URL.",
            ),
        ),
        migrations.AddField(
            model_name='contact',
            name='portal_active',
            field=models.BooleanField(
                default=False,
                help_text="Enable individual portal access for this contact. "
                          "Automatically unusable if the parent client's portal access is revoked.",
            ),
        ),
    ]
