# Reconstructed bridge migration — original created on production, never synced
# here. Recreated from the current model definition. DO NOT deploy to production.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0006_client_portal_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='portal_linked_clients',
            field=models.ManyToManyField(
                blank=True,
                related_name='portal_linked_by',
                to='clients.client',
                help_text="Other client records whose projects/invoices/etc. should also appear in this client's portal (e.g. one person who owns multiple companies).",
            ),
        ),
    ]
