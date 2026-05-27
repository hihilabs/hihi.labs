import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='WikiSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('content_md', models.TextField(blank=True)),
                ('diagram_mermaid', models.TextField(blank=True)),
                ('order', models.IntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wiki_sections', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['order', 'title']},
        ),
    ]
