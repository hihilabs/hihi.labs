from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('audio_file', models.FileField(upload_to='tracks/')),
                ('duration_s', models.FloatField(default=0)),
                ('bpm', models.IntegerField(blank=True, null=True)),
                ('key', models.CharField(blank=True, max_length=4)),
                ('tags', models.CharField(blank=True, help_text='Comma-separated', max_length=300)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracks', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tracks', to='projects.project')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='TrackComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp_s', models.FloatField()),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='sound.track')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='track_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['timestamp_s']},
        ),
    ]
