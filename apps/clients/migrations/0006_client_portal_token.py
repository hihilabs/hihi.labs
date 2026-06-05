import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0005_alter_client_hosted_domain_alter_client_id_and_more'),
    ]

    operations = [
        migrations.AddField(
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
