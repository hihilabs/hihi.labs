# Reconstructed bridge migration — the original 0007 was created on production and
# never synced to this dev copy. Recreated from the current model definition so the
# local graph matches production's filenames. DO NOT deploy to production (it has
# its own 0007 already applied).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_task_client_visible'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='entity',
            field=models.CharField(
                choices=[
                    ('binsky', 'Binsky'),
                    ('fckry', 'FCKRY LLC'),
                    ('community', 'Community Playlist'),
                    ('clients', 'Clients'),
                    ('general', 'General'),
                ],
                db_index=True,
                default='general',
                max_length=20,
            ),
        ),
    ]
