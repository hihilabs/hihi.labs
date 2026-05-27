import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('company', models.CharField(blank=True, max_length=200)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('website', models.URLField(blank=True, max_length=500)),
                ('address', models.TextField(blank=True)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('country', models.CharField(blank=True, max_length=100)),
                ('notes', models.TextField(blank=True)),
                ('color', models.CharField(default='#7c6af7', max_length=7)),
                ('status', models.CharField(choices=[('lead','Lead'),('active','Active'),('inactive','Inactive'),('archived','Archived')], default='active', max_length=20)),
                ('hosted_domain', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clients', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('role', models.CharField(blank=True, max_length=100)),
                ('is_primary', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='clients.client')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-is_primary', 'first_name']},
        ),
        migrations.CreateModel(
            name='HostingSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('domain', models.CharField(max_length=200)),
                ('additional_domains', models.TextField(blank=True)),
                ('plan_name', models.CharField(default='VPS Hosting', max_length=100)),
                ('price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('billing_cycle', models.CharField(choices=[('monthly','Monthly'),('annual','Annual'),('one-time','One-time')], default='monthly', max_length=20)),
                ('previous_provider', models.CharField(blank=True, max_length=100)),
                ('server_path', models.CharField(blank=True, max_length=300)),
                ('notes', models.TextField(blank=True)),
                ('started', models.DateField(blank=True, null=True)),
                ('next_invoice_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hosting_subscriptions', to='clients.client')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hosting_subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['domain']},
        ),
    ]
