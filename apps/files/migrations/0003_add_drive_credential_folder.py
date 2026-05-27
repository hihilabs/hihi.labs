import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('files', '0002_clientfile_drive_file_id_and_more'),
        ('clients', '0004_add_lead_archived_status'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='DriveCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('access_token', models.TextField()),
                ('refresh_token', models.TextField(blank=True)),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='drive_credential', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DriveFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('drive_folder_id', models.CharField(max_length=200)),
                ('name', models.CharField(max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='drive_folders', to='clients.client')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drive_folders', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='drive_folders', to='projects.project')),
            ],
            options={'ordering': ['name']},
        ),
    ]
