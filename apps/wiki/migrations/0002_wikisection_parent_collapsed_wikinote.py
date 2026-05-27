import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('wiki', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='wikisection',
            name='parent',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='children',
                to='wiki.wikisection',
            ),
        ),
        migrations.AddField(
            model_name='wikisection',
            name='collapsed',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='WikiNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('body', models.TextField()),
                ('pinned', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('section', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notes',
                    to='wiki.wikisection',
                )),
            ],
            options={'ordering': ['-pinned', '-created_at']},
        ),
    ]
