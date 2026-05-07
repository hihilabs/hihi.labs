from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('host', models.CharField(max_length=255)),
                ('ssh_user', models.CharField(default='root', max_length=100)),
                ('port', models.IntegerField(default=22)),
                ('tags', models.CharField(blank=True, max_length=200)),
                ('notes', models.TextField(blank=True)),
                ('icon', models.CharField(default='fa-server', max_length=40)),
                ('color', models.CharField(default='#7c6af7', max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='servers', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['name']},
        ),
    ]
