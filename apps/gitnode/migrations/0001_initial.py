from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('servers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagedRepo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('path', models.CharField(help_text='Absolute path on the server', max_length=500)),
                ('branch', models.CharField(default='master', max_length=100)),
                ('color', models.CharField(default='#7c6af7', max_length=7)),
                ('icon', models.CharField(default='fa-code-branch', max_length=40)),
                ('github_url', models.URLField(blank=True)),
                ('service_name', models.CharField(blank=True, help_text='systemd service to restart after deploy', max_length=100)),
                ('order', models.PositiveIntegerField(default=0)),
                ('active', models.BooleanField(default=True)),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repos', to='servers.server')),
            ],
            options={'ordering': ['order', 'name']},
        ),
    ]
