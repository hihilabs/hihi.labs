import csv
import json
from collections import defaultdict
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Expense


@login_required
def index(request):
    year = int(request.GET.get('year', date.today().year))
    cat_filter = request.GET.get('cat', '')

    qs = Expense.objects.filter(owner=request.user, date__year=year)
    if cat_filter:
        qs = qs.filter(category=cat_filter)

    expenses = list(qs)

    # Summary by category (all expenses for the year, regardless of filter)
    all_year = Expense.objects.filter(owner=request.user, date__year=year)
    by_cat = defaultdict(lambda: {'total': 0, 'deductible': 0})
    for e in all_year:
        by_cat[e.category]['total'] += float(e.amount)
        if e.is_deductible:
            by_cat[e.category]['deductible'] += float(e.amount)

    total_all = sum(float(e.amount) for e in all_year)
    total_deductible = sum(float(e.amount) for e in all_year if e.is_deductible)

    years = (
        Expense.objects.filter(owner=request.user)
        .dates('date', 'year')
    )
    year_list = sorted({d.year for d in years} | {date.today().year}, reverse=True)

    return render(request, 'tax/index.html', {
        'expenses': expenses,
        'categories': Expense.CATEGORIES,
        'by_cat': dict(by_cat),
        'total_all': total_all,
        'total_deductible': total_deductible,
        'year': year,
        'year_list': year_list,
        'cat_filter': cat_filter,
    })


@login_required
@require_POST
def expense_add(request):
    data = json.loads(request.body)
    e = Expense.objects.create(
        owner=request.user,
        date=data.get('date') or date.today(),
        amount=data.get('amount', 0),
        vendor=data.get('vendor', '').strip(),
        description=data.get('description', '').strip(),
        category=data.get('category', 'other'),
        is_deductible=data.get('is_deductible', True),
    )
    return JsonResponse({
        'id': e.pk,
        'date': str(e.date),
        'vendor': e.vendor,
        'amount': float(e.amount),
        'category': e.get_category_display(),
        'is_deductible': e.is_deductible,
    })


@login_required
@require_POST
def expense_delete(request, pk):
    get_object_or_404(Expense, pk=pk, owner=request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def expense_toggle(request, pk):
    e = get_object_or_404(Expense, pk=pk, owner=request.user)
    e.is_deductible = not e.is_deductible
    e.save(update_fields=['is_deductible'])
    return JsonResponse({'is_deductible': e.is_deductible})


@login_required
def expense_csv(request):
    year = int(request.GET.get('year', date.today().year))
    expenses = Expense.objects.filter(owner=request.user, date__year=year).order_by('date')

    def rows():
        yield 'Date,Vendor,Description,Category,Amount,Deductible\r\n'
        for e in expenses:
            yield f'{e.date},{e.vendor},{e.description},{e.get_category_display()},{e.amount},{"Yes" if e.is_deductible else "No"}\r\n'

    resp = StreamingHttpResponse(rows(), content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="expenses_{year}.csv"'
    return resp
