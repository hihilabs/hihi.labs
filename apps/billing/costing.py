"""Cost & pricing math for the value board's cost / sustain / pricing modes.

All functions return plain floats so the view/template layer never has to mix
Decimal and float. Everything degrades to 0 when no cost data is entered yet —
the board still renders, costs just read low until the inputs are filled in.

Levels (see BILLING_MODE.md):
  L1 raw_cost          — what delivering the project has cost to date
  L2 sustain_monthly   — monthly run-rate to keep the project alive
  L3 suggested_pricing — price derived from cost floor x margin x client factor
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import CostSettings, ProjectExpense

# Never price below cost x this, regardless of margin/factor inputs.
PRICE_FLOOR_MULT = 1.2
# A project is flagged underpriced when its current rate is below this share
# of the suggested rate.
UNDERPRICED_THRESHOLD = 0.8


def get_cost_settings():
    return CostSettings.load()


def _f(x):
    return float(x or 0)


def ai_cost(project, settings):
    """Token spend of conversations attributed to this project, in dollars."""
    from apps.claude_ai.models import Message
    tokens = Message.objects.filter(conversation__project=project).aggregate(
        t=Sum('tokens_used'))['t'] or 0
    return tokens * _f(settings.ai_cost_per_1k_tokens) / 1000


def infra_monthly(project):
    """This project's share of linked servers' monthly cost (split evenly)."""
    total = 0.0
    for server in project.servers.all():
        n = server.projects.count()
        if n:
            total += _f(server.monthly_cost) / n
    return total


def services_monthly(project):
    return _f(project.project_services.filter(enabled=True)
              .aggregate(t=Sum('monthly_cost'))['t'])


def expenses(project):
    """Returns (one_time_total, monthly_recurring_total)."""
    one_time = _f(project.expenses.filter(kind='one_time')
                  .aggregate(t=Sum('amount'))['t'])
    monthly = _f(project.expenses.filter(kind='monthly')
                 .aggregate(t=Sum('amount'))['t'])
    return one_time, monthly


def raw_cost(project, settings, total_hours):
    """L1: cost to date = labor + AI + one-time expenses.

    Recurring costs are reported separately (recurring_monthly) rather than
    multiplied out over the project's age — they belong to L2.
    """
    labor = total_hours * _f(settings.labor_cost_per_hour)
    ai = ai_cost(project, settings)
    one_time, monthly_exp = expenses(project)
    total = labor + ai + one_time
    return {
        'labor': round(labor, 2),
        'ai': round(ai, 2),
        'one_time_expenses': round(one_time, 2),
        'total': round(total, 2),
        'recurring_monthly': round(
            monthly_exp + services_monthly(project) + infra_monthly(project), 2),
    }


def maintenance_hours_monthly(project):
    """Average hours/month over the trailing 90 days of closed time entries."""
    cutoff = timezone.now() - timedelta(days=90)
    secs = sum(
        e.duration_seconds()
        for e in project.time_entries.filter(ended_at__isnull=False,
                                             started_at__gte=cutoff))
    return secs / 3600 / 3


def sustain_monthly(project, settings, active_project_count):
    """L2: monthly run-rate to keep this project alive."""
    maint_hours = maintenance_hours_monthly(project)
    labor = maint_hours * _f(settings.labor_cost_per_hour)
    _, monthly_exp = expenses(project)
    infra = infra_monthly(project)
    services = services_monthly(project)
    overhead = (_f(settings.overhead_monthly) / active_project_count
                if active_project_count else 0)
    total = labor + monthly_exp + infra + services + overhead
    return {
        'maint_hours': round(maint_hours, 1),
        'labor': round(labor, 2),
        'recurring_expenses': round(monthly_exp + services, 2),
        'infra': round(infra, 2),
        'overhead': round(overhead, 2),
        'total': round(total, 2),
    }


def client_factor(project, settings):
    client = project.client_fk
    if client and client.pricing_factor:
        return _f(client.pricing_factor)
    return _f(settings.default_client_factor) or 1.0


def suggested_pricing(project, settings, sustain_total):
    """L3: suggested hourly rate + monthly retainer vs the current rate."""
    margin = 1 + _f(settings.target_margin_pct) / 100
    factor = client_factor(project, settings)
    labor_cost = _f(settings.labor_cost_per_hour)

    hourly = max(labor_cost * margin * factor, labor_cost * PRICE_FLOOR_MULT)
    retainer = max(sustain_total * margin * factor, sustain_total * PRICE_FLOOR_MULT)

    current = _f(project.hourly_rate)
    delta_pct = round((hourly - current) / current * 100) if current else None
    return {
        'factor': factor,
        'suggested_hourly': round(hourly, 2),
        'suggested_retainer': round(retainer, 2),
        'current_hourly': current,
        'hourly_delta_pct': delta_pct,
        'underpriced': bool(current) and current < hourly * UNDERPRICED_THRESHOLD,
    }
