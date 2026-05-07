import json
import hashlib
import hmac
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Plan, Subscription, PaymentRecord

logger = logging.getLogger(__name__)


@login_required
def index(request):
    plans = Plan.objects.filter(is_active=True)
    sub = getattr(request, 'subscription', None)
    payments = sub.payments.all()[:10] if sub else []
    return render(request, 'subscriptions/index.html', {
        'plans': plans,
        'sub': sub,
        'payments': payments,
    })


@login_required
def upgrade(request):
    plans = Plan.objects.filter(is_active=True)
    sub = getattr(request, 'subscription', None)
    return render(request, 'subscriptions/upgrade.html', {
        'plans': plans,
        'sub': sub,
        'phantom_address': getattr(settings, 'PHANTOM_WALLET_ADDRESS', ''),
        'helium_address': getattr(settings, 'HELIUM_WALLET_ADDRESS', ''),
        'stripe_pub_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
    })


# ── Phantom (Solana) ──────────────────────────────────────────────────────────

@login_required
@require_POST
def phantom_submit(request):
    """User sends SOL, submits tx signature for on-chain verification."""
    data = json.loads(request.body)
    tx_sig = data.get('tx_signature', '').strip()
    plan_id = data.get('plan_id')
    wallet = data.get('wallet_address', '').strip()

    if not tx_sig or not plan_id:
        return JsonResponse({'error': 'Missing fields'}, status=400)

    plan = get_object_or_404(Plan, pk=plan_id)

    # Verify on Solana mainnet via public RPC
    confirmed = _verify_solana_tx(tx_sig, wallet, float(plan.price_sol))
    if not confirmed:
        return JsonResponse({'error': 'Transaction not confirmed on-chain'}, status=400)

    sub, _ = Subscription.objects.get_or_create(
        user=request.user,
        defaults={'plan': plan, 'status': 'active', 'gateway': 'phantom'},
    )
    sub.plan = plan
    sub.status = 'active'
    sub.gateway = 'phantom'
    sub.wallet_address = wallet
    sub.current_period_start = timezone.now()
    sub.current_period_end = timezone.now() + timedelta(days=30)
    sub.save()

    PaymentRecord.objects.create(
        subscription=sub,
        gateway='phantom',
        amount_crypto=plan.price_sol,
        currency='SOL',
        tx_hash=tx_sig,
        status='confirmed',
        period_start=sub.current_period_start,
        period_end=sub.current_period_end,
        paid_at=timezone.now(),
    )

    return JsonResponse({'ok': True, 'plan': plan.name})


def _verify_solana_tx(signature, expected_sender, expected_sol):
    """Check Solana mainnet for a confirmed transaction."""
    rpc = 'https://api.mainnet-beta.solana.com'
    payload = {
        'jsonrpc': '2.0', 'id': 1,
        'method': 'getTransaction',
        'params': [signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}],
    }
    try:
        r = requests.post(rpc, json=payload, timeout=10)
        result = r.json().get('result')
        if not result or result.get('meta', {}).get('err'):
            return False

        # Confirm the SOL transfer exists and amount is >= expected
        lamports_expected = int(expected_sol * 1_000_000_000)
        pre = result['meta']['preBalances']
        post = result['meta']['postBalances']
        # First account is the fee payer/sender; look for a net decrease >= expected
        if pre and post and (pre[0] - post[0]) >= lamports_expected:
            return True
    except Exception as e:
        logger.warning('[Phantom verify] %s', e)
    return False


# ── Helium (HNT) ─────────────────────────────────────────────────────────────

@login_required
@require_POST
def helium_submit(request):
    """User sends HNT, submits tx hash. We mark pending; admin confirms."""
    data = json.loads(request.body)
    tx_hash = data.get('tx_hash', '').strip()
    plan_id = data.get('plan_id')
    wallet = data.get('wallet_address', '').strip()

    if not tx_hash or not plan_id:
        return JsonResponse({'error': 'Missing fields'}, status=400)

    plan = get_object_or_404(Plan, pk=plan_id)

    sub, _ = Subscription.objects.get_or_create(
        user=request.user,
        defaults={'plan': plan, 'status': 'trialing', 'gateway': 'helium'},
    )

    PaymentRecord.objects.create(
        subscription=sub,
        gateway='helium',
        amount_crypto=plan.price_hnt,
        currency='HNT',
        tx_hash=tx_hash,
        status='pending',
    )

    # TODO: wire Helium blockchain API verification when endpoint is known
    # For now: pings Discord ops webhook so Andrew can manually confirm
    _notify_helium_pending(request.user, plan, tx_hash)

    return JsonResponse({'ok': True, 'pending': True, 'message': 'Payment submitted — you\'ll be activated within 1 hour.'})


def _notify_helium_pending(user, plan, tx_hash):
    webhook = getattr(settings, 'DISCORD_WEBHOOK_OPS', '')
    if not webhook:
        return
    try:
        requests.post(webhook, json={
            'content': f'🔮 **Helium payment pending**\nUser: `{user.username}` → Plan: `{plan.name}`\nTX: `{tx_hash}`\nConfirm at `/admin/subscriptions/paymentrecord/`'
        }, timeout=5)
    except Exception:
        pass


# ── Stripe ────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def stripe_create_session(request):
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
    except ImportError:
        return JsonResponse({'error': 'Stripe not installed — add stripe to requirements.txt'}, status=500)

    data = json.loads(request.body)
    plan = get_object_or_404(Plan, pk=data.get('plan_id'))

    if not plan.stripe_price_id:
        return JsonResponse({'error': 'No Stripe price configured for this plan'}, status=400)

    session = stripe.checkout.Session.create(
        customer_email=request.user.email,
        payment_method_types=['card'],
        payment_method_options={
            'card': {'request_three_d_secure': 'automatic'},
        },
        line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
        mode='subscription',
        success_url=request.build_absolute_uri('/subscriptions/?stripe=success'),
        cancel_url=request.build_absolute_uri('/subscriptions/upgrade/'),
        metadata={'user_id': request.user.pk, 'plan_id': plan.pk},
    )
    return JsonResponse({'session_url': session.url})


@csrf_exempt
def stripe_webhook(request):
    sig = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(request.body, sig, secret)
    except Exception as e:
        logger.warning('[Stripe webhook] %s', e)
        return HttpResponse(status=400)

    et = event['type']
    obj = event['data']['object']

    if et == 'checkout.session.completed':
        _stripe_activate(obj)
    elif et in ('invoice.paid',):
        _stripe_renew(obj)
    elif et in ('customer.subscription.deleted', 'customer.subscription.paused'):
        _stripe_cancel(obj)
    elif et == 'invoice.payment_failed':
        _stripe_past_due(obj)

    return HttpResponse(status=200)


def _stripe_activate(session):
    from django.contrib.auth.models import User
    uid = session.get('metadata', {}).get('user_id')
    plan_id = session.get('metadata', {}).get('plan_id')
    if not uid or not plan_id:
        return
    try:
        user = User.objects.get(pk=uid)
        plan = Plan.objects.get(pk=plan_id)
    except Exception:
        return
    sub, _ = Subscription.objects.get_or_create(user=user, defaults={'plan': plan})
    sub.plan = plan
    sub.status = 'active'
    sub.gateway = 'stripe'
    sub.stripe_customer_id = session.get('customer', '')
    sub.stripe_subscription_id = session.get('subscription', '')
    sub.current_period_start = timezone.now()
    sub.current_period_end = timezone.now() + timedelta(days=30)
    sub.save()
    PaymentRecord.objects.create(
        subscription=sub, gateway='stripe',
        amount_usd=plan.price_usd, currency='USD',
        gateway_reference=session.get('id', ''),
        status='confirmed', paid_at=timezone.now(),
    )


def _stripe_renew(invoice):
    stripe_sub_id = invoice.get('subscription', '')
    if not stripe_sub_id:
        return
    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
        sub.status = 'active'
        sub.current_period_end = timezone.now() + timedelta(days=30)
        sub.save(update_fields=['status', 'current_period_end', 'updated_at'])
        PaymentRecord.objects.create(
            subscription=sub, gateway='stripe',
            amount_usd=sub.plan.price_usd, currency='USD',
            gateway_reference=invoice.get('id', ''),
            status='confirmed', paid_at=timezone.now(),
        )
    except Subscription.DoesNotExist:
        pass


def _stripe_cancel(stripe_sub):
    stripe_sub_id = stripe_sub.get('id', '')
    Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).update(status='canceled')


def _stripe_past_due(invoice):
    stripe_sub_id = invoice.get('subscription', '')
    Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).update(status='past_due')


# ── Admin: confirm Helium manually ───────────────────────────────────────────

@login_required
@require_POST
def admin_confirm_helium(request, payment_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    pmt = get_object_or_404(PaymentRecord, pk=payment_id, gateway='helium')
    pmt.status = 'confirmed'
    pmt.paid_at = timezone.now()
    pmt.save()
    sub = pmt.subscription
    sub.status = 'active'
    sub.plan = sub.plan
    sub.current_period_start = timezone.now()
    sub.current_period_end = timezone.now() + timedelta(days=30)
    sub.save()
    return JsonResponse({'ok': True})
