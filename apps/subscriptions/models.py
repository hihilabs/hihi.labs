from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


FEATURES = [
    'chat',
    'templates',
    'voice',
    'projects',
    'billing',
    'sound',
    'server',
    'tax',
    'messaging',
    'subscriptions',
]

PLAN_DEFAULTS = [
    {
        'tier': 'free',
        'name': 'Free',
        'price_usd': '0.00',
        'price_sol': '0.000000',
        'price_hnt': '0.000000',
        'features': ['chat'],
        'stripe_price_id': '',
    },
    {
        'tier': 'starter',
        'name': 'Starter',
        'price_usd': '29.00',
        'price_sol': '0.200000',
        'price_hnt': '1.000000',
        'features': ['chat', 'templates', 'voice', 'projects'],
        'stripe_price_id': '',
    },
    {
        'tier': 'pro',
        'name': 'Pro',
        'price_usd': '79.00',
        'price_sol': '0.500000',
        'price_hnt': '2.500000',
        'features': ['chat', 'templates', 'voice', 'projects', 'billing', 'sound', 'messaging'],
        'stripe_price_id': '',
    },
    {
        'tier': 'agency',
        'name': 'Agency',
        'price_usd': '149.00',
        'price_sol': '1.000000',
        'price_hnt': '5.000000',
        'features': FEATURES,
        'stripe_price_id': '',
    },
]


class Plan(models.Model):
    TIERS = [('free', 'Free'), ('starter', 'Starter'), ('pro', 'Pro'), ('agency', 'Agency')]
    tier = models.CharField(max_length=20, choices=TIERS, unique=True)
    name = models.CharField(max_length=50)
    price_usd = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    price_sol = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    price_hnt = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    features = models.JSONField(default=list)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['price_usd']

    def __str__(self):
        return f'{self.name} (${self.price_usd}/mo)'

    def has_feature(self, feature):
        return feature in (self.features or [])


class Subscription(models.Model):
    STATUS = [
        ('active', 'Active'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
    ]
    GATEWAY = [
        ('stripe', 'Stripe'),
        ('phantom', 'Phantom / SOL'),
        ('helium', 'Helium / HNT'),
        ('manual', 'Manual'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    gateway = models.CharField(max_length=20, choices=GATEWAY, blank=True)

    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)

    # Crypto
    wallet_address = models.CharField(max_length=200, blank=True)

    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} — {self.plan.name} ({self.status})'

    def is_active(self):
        return self.status in ('active', 'trialing')

    def has_feature(self, feature):
        if not self.is_active():
            return False
        return self.plan.has_feature(feature)

    def enabled_features(self):
        if not self.is_active():
            return set()
        return set(self.plan.features or [])


class PaymentRecord(models.Model):
    STATUS = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('failed', 'Failed'), ('refunded', 'Refunded')]
    GATEWAY = [('stripe', 'Stripe'), ('phantom', 'Phantom / SOL'), ('helium', 'Helium / HNT'), ('manual', 'Manual')]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    gateway = models.CharField(max_length=20, choices=GATEWAY)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_crypto = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    currency = models.CharField(max_length=10, default='USD')  # USD, SOL, HNT
    tx_hash = models.CharField(max_length=300, blank=True)
    gateway_reference = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.subscription.user.username} — {self.gateway} {self.currency} ({self.status})'
