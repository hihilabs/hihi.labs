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
            name='Plan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tier', models.CharField(choices=[('free', 'Free'), ('starter', 'Starter'), ('pro', 'Pro'), ('agency', 'Agency')], max_length=20, unique=True)),
                ('name', models.CharField(max_length=50)),
                ('price_usd', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('price_sol', models.DecimalField(decimal_places=6, default=0, max_digits=12)),
                ('price_hnt', models.DecimalField(decimal_places=6, default=0, max_digits=12)),
                ('features', models.JSONField(default=list)),
                ('stripe_price_id', models.CharField(blank=True, max_length=100)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['price_usd']},
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'Active'), ('trialing', 'Trialing'), ('past_due', 'Past Due'), ('canceled', 'Canceled')], default='active', max_length=20)),
                ('gateway', models.CharField(blank=True, choices=[('stripe', 'Stripe'), ('phantom', 'Phantom / SOL'), ('helium', 'Helium / HNT'), ('manual', 'Manual')], max_length=20)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=100)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=100)),
                ('wallet_address', models.CharField(blank=True, max_length=200)),
                ('current_period_start', models.DateTimeField(blank=True, null=True)),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='subscriptions.plan')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gateway', models.CharField(choices=[('stripe', 'Stripe'), ('phantom', 'Phantom / SOL'), ('helium', 'Helium / HNT'), ('manual', 'Manual')], max_length=20)),
                ('amount_usd', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('amount_crypto', models.DecimalField(blank=True, decimal_places=8, max_digits=18, null=True)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('tx_hash', models.CharField(blank=True, max_length=300)),
                ('gateway_reference', models.CharField(blank=True, max_length=300)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('period_start', models.DateTimeField(blank=True, null=True)),
                ('period_end', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='subscriptions.subscription')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
