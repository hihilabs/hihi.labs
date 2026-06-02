import json
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Bill, BillPayment, CachedAccount, SavingsGoal, SequenceConnection
from .sequence import SequenceAPIError, SequenceClient


@login_required
def dashboard(request):
    connection = SequenceConnection.objects.filter(user=request.user).first()

    personal_total = 0
    business_total = 0
    total_debt = 0
    if connection:
        for a in connection.accounts.filter(account_type='external'):
            if a.account_subtype in ('loan', 'credit'):
                total_debt += a.balance_cents
            elif a.is_business:
                business_total += a.balance_cents
            elif a.account_subtype in ('cash', 'crypto'):
                personal_total += a.balance_cents

    bills = Bill.objects.filter(user=request.user, is_active=True)
    bills_data = []
    overdue_count = 0
    paid_count = 0
    total_monthly_cents = 0
    for bill in bills:
        paid = bill.paid_this_month()
        overdue = bill.is_overdue()
        if paid:
            paid_count += 1
        elif overdue:
            overdue_count += 1
        total_monthly_cents += bill.amount_cents
        bills_data.append({'bill': bill, 'paid': paid, 'overdue': overdue})

    goals = SavingsGoal.objects.filter(user=request.user, is_active=True)

    return render(request, 'pepperjuice/dashboard.html', {
        'connection': connection,
        'personal_total': personal_total / 100,
        'business_total': business_total / 100,
        'total_debt': total_debt / 100,
        'bills': bills_data,
        'overdue_count': overdue_count,
        'paid_count': paid_count,
        'total_bills': bills.count(),
        'total_monthly': total_monthly_cents / 100,
        'goals': goals,
    })


@login_required
def bills_view(request):
    bills = Bill.objects.filter(user=request.user, is_active=True)
    bills_data = []
    for bill in bills:
        paid = bill.paid_this_month()
        bills_data.append({
            'bill': bill,
            'paid': paid,
            'overdue': bill.is_overdue(),
            'last_payment': bill.payments.first(),
        })

    personal_monthly = sum(b['bill'].amount_cents for b in bills_data if not b['bill'].is_business)
    business_monthly = sum(b['bill'].amount_cents for b in bills_data if b['bill'].is_business)

    return render(request, 'pepperjuice/bills.html', {
        'bills': bills_data,
        'personal_monthly': personal_monthly / 100,
        'business_monthly': business_monthly / 100,
        'categories': Bill.CATEGORIES,
    })


@login_required
@require_POST
def bill_save(request):
    data = json.loads(request.body)
    pk = data.get('pk')
    bill = get_object_or_404(Bill, pk=pk, user=request.user) if pk else Bill(user=request.user)
    bill.name = data['name'].strip()
    bill.amount_cents = int(float(data['amount']) * 100)
    bill.due_day = int(data['due_day'])
    bill.category = data.get('category', 'other')
    bill.is_auto_pay = bool(data.get('is_auto_pay'))
    bill.is_business = bool(data.get('is_business'))
    bill.notes = data.get('notes', '').strip()
    bill.sequence_rule_id = data.get('sequence_rule_id', '').strip()
    bill.save()
    return JsonResponse({'ok': True, 'pk': bill.pk})


@login_required
@require_POST
def bill_delete(request, pk):
    bill = get_object_or_404(Bill, pk=pk, user=request.user)
    bill.is_active = False
    bill.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def bill_mark_paid(request, pk):
    bill = get_object_or_404(Bill, pk=pk, user=request.user)
    data = json.loads(request.body)
    BillPayment.objects.create(
        bill=bill,
        paid_date=date.today(),
        amount_cents=int(float(data.get('amount', bill.amount_cents / 100)) * 100),
        note=data.get('note', ''),
    )
    return JsonResponse({'ok': True})


@login_required
def goals_view(request):
    goals = SavingsGoal.objects.filter(user=request.user, is_active=True)
    total_needed = sum(g.target_cents for g in goals)
    total_saved = sum(g.current_cents for g in goals)
    total_monthly = sum(g.monthly_contribution_cents for g in goals)

    return render(request, 'pepperjuice/goals.html', {
        'goals': goals,
        'total_needed': total_needed / 100,
        'total_saved': total_saved / 100,
        'total_monthly': total_monthly / 100,
        'goal_types': SavingsGoal.GOAL_TYPES,
    })


@login_required
@require_POST
def goal_save(request):
    data = json.loads(request.body)
    pk = data.get('pk')
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user) if pk else SavingsGoal(user=request.user)
    goal.name = data['name'].strip()
    goal.goal_type = data.get('goal_type', 'other')
    goal.target_cents = int(float(data['target']) * 100)
    goal.current_cents = int(float(data.get('current', 0)) * 100)
    goal.monthly_contribution_cents = int(float(data.get('monthly', 0)) * 100)
    goal.notes = data.get('notes', '').strip()
    goal.sequence_account_id = data.get('sequence_account_id', '').strip()
    goal.target_date = datetime.strptime(data['target_date'], '%Y-%m-%d').date() if data.get('target_date') else None
    goal.save()
    return JsonResponse({'ok': True, 'pk': goal.pk})


@login_required
@require_POST
def goal_delete(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    goal.is_active = False
    goal.save()
    return JsonResponse({'ok': True})


@login_required
def accounts_view(request):
    connection = SequenceConnection.objects.filter(user=request.user).first()
    accounts = connection.accounts.all() if connection else []
    return render(request, 'pepperjuice/accounts.html', {
        'connection': connection,
        'accounts': accounts,
        'subtype_choices': CachedAccount.SUBTYPE_CHOICES,
    })


@login_required
@require_POST
def sync_accounts(request):
    connection = SequenceConnection.objects.filter(user=request.user).first()
    if not connection:
        return JsonResponse({'error': 'No Sequence connection configured.'}, status=400)

    try:
        client = SequenceClient(connection.api_key)
        data = client.get_accounts()

        # Response shape: {"message":"OK","data":{"accounts":[...]}}
        # Balance shape: {"amountInDollars": 123.45, "error": null}
        raw_list = data.get('data', {}).get('accounts', [])
        if not raw_list and isinstance(data, list):
            raw_list = data  # fallback for any API version change

        seen_ids = []
        balance_map = {}  # seq_id → balance_cents

        TYPE_MAP = {
            'account': 'external',
            'income source': 'income',
            'income_source': 'income',
            'pod': 'pod',
        }

        def safe_cents(val):
            if val is None:
                return 0
            try:
                return int(float(str(val).replace(',', '')) * 100)
            except (ValueError, TypeError):
                return 0

        def detect_subtype(name, acct_type, institution=''):
            if acct_type == 'pod':
                return 'bucket'
            if acct_type == 'income':
                return 'other'
            n = name.lower()
            inst = institution.lower()
            if 'credit card' in n:
                return 'credit'
            if 'loan' in n or 'loan' in inst:
                return 'loan'
            if '401' in n or 'ira' in n or 'tod' in n or 'individual' in n or 'fidelity' in inst or 'vanguard' in inst:
                return 'investment'
            if 'kraken' in inst or 'coinbase' in inst or 'crypto' in n or 'bitcoin' in n:
                return 'crypto'
            if 'checking' in n or 'savings' in n or 'bank' in inst or 'credit union' in inst or 'paypal' in n:
                return 'cash'
            return 'other'

        for acct in raw_list:
            seq_id = str(acct.get('id') or acct.get('accountId') or acct.get('uuid') or '')
            if not seq_id:
                continue

            # Balance is nested: {"amountInDollars": 123.45, "error": null}
            bal_obj = acct.get('balance') or {}
            if isinstance(bal_obj, dict):
                dollars = bal_obj.get('amountInDollars')
            else:
                dollars = bal_obj  # flat value fallback
            balance_cents = safe_cents(dollars)

            raw_type = (acct.get('type') or 'pod').lower().strip()
            acct_type = TYPE_MAP.get(raw_type, 'pod')
            name = acct.get('name', 'Unknown')
            institution = acct.get('institution', '')
            subtype = detect_subtype(name, acct_type, institution)

            obj, created = CachedAccount.objects.update_or_create(
                connection=connection,
                sequence_id=seq_id,
                defaults={
                    'name': name,
                    'institution': institution,
                    'account_type': acct_type,
                    'balance_cents': balance_cents,
                    'currency': acct.get('currency', 'USD'),
                },
            )
            # Set subtype on creation or if still unclassified; preserve manual overrides
            if created or obj.account_subtype == 'other':
                obj.account_subtype = subtype
                obj.save(update_fields=['account_subtype'])
            seen_ids.append(seq_id)
            balance_map[seq_id] = balance_cents

        # Auto-update any savings goals linked to a Sequence account
        goals_updated = 0
        for goal in SavingsGoal.objects.filter(user=request.user, is_active=True).exclude(sequence_account_id=''):
            if goal.sequence_account_id in balance_map:
                goal.current_cents = balance_map[goal.sequence_account_id]
                goal.save(update_fields=['current_cents'])
                goals_updated += 1

        connection.last_sync = timezone.now()
        connection.save()
        return JsonResponse({'ok': True, 'count': len(seen_ids), 'goals_updated': goals_updated})

    except SequenceAPIError as e:
        return JsonResponse({'ok': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'{type(e).__name__}: {e}'})


@login_required
@require_POST
def account_toggle_business(request, pk):
    account = get_object_or_404(CachedAccount, pk=pk, connection__user=request.user)
    account.is_business = not account.is_business
    account.save()
    return JsonResponse({'ok': True, 'is_business': account.is_business})


@login_required
@require_POST
def account_set_subtype(request, pk):
    account = get_object_or_404(CachedAccount, pk=pk, connection__user=request.user)
    data = json.loads(request.body)
    valid = [c[0] for c in CachedAccount.SUBTYPE_CHOICES]
    subtype = data.get('subtype', '')
    if subtype not in valid:
        return JsonResponse({'ok': False, 'error': 'Invalid subtype'})
    account.account_subtype = subtype
    account.save(update_fields=['account_subtype'])
    return JsonResponse({'ok': True, 'subtype': account.account_subtype})


@login_required
def connect_view(request):
    connection = SequenceConnection.objects.filter(user=request.user).first()
    if request.method == 'POST':
        api_key = request.POST.get('api_key', '').strip()
        display_name = request.POST.get('display_name', '').strip()
        if api_key:
            SequenceConnection.objects.update_or_create(
                user=request.user,
                defaults={'api_key': api_key, 'display_name': display_name},
            )
            messages.success(request, 'Sequence connected.')
            return redirect('pepperjuice:dashboard')
    return render(request, 'pepperjuice/connect.html', {'connection': connection})


@login_required
@require_POST
def disconnect(request):
    SequenceConnection.objects.filter(user=request.user).delete()
    messages.success(request, 'Sequence disconnected.')
    return redirect('pepperjuice:connect')
