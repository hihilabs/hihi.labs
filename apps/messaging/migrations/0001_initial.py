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
            name='Thread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(blank=True, max_length=500)),
                ('source', models.CharField(choices=[('internal', 'Internal'), ('gmail', 'Gmail'), ('proton', 'Proton Mail'), ('email', 'Email')], default='internal', max_length=20)),
                ('external_thread_id', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_threads', to=settings.AUTH_USER_MODEL)),
                ('participants', models.ManyToManyField(blank=True, related_name='threads', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='threads', to='projects.project')),
            ],
            options={'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('html_body', models.TextField(blank=True)),
                ('from_email', models.CharField(blank=True, max_length=300)),
                ('external_message_id', models.CharField(blank=True, max_length=500)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('thread', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='messaging.thread')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL)),
                ('read_by', models.ManyToManyField(blank=True, related_name='read_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['sent_at']},
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('invoice_paid', 'Invoice Paid'), ('invoice_sent', 'Invoice Sent'), ('invoice_overdue', 'Invoice Overdue'), ('timer_stopped', 'Timer Stopped'), ('task_done', 'Task Completed'), ('message', 'New Message'), ('subscription_renewed', 'Subscription Renewed'), ('subscription_expired', 'Subscription Expired'), ('subscription_pending', 'Payment Pending'), ('system', 'System')], max_length=30)),
                ('title', models.CharField(max_length=200)),
                ('body', models.CharField(blank=True, max_length=500)),
                ('link', models.CharField(blank=True, max_length=300)),
                ('read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='EmailAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('gmail', 'Gmail'), ('proton', 'Proton (Bridge)'), ('imap', 'Generic IMAP')], max_length=20)),
                ('label', models.CharField(max_length=50)),
                ('email_address', models.EmailField()),
                ('imap_host', models.CharField(max_length=200)),
                ('imap_port', models.IntegerField(default=993)),
                ('imap_user', models.CharField(max_length=200)),
                ('imap_password', models.CharField(max_length=500)),
                ('use_ssl', models.BooleanField(default=True)),
                ('last_synced', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['label']},
        ),
    ]
