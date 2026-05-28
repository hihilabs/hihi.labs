"""Superuser bypass helpers — read operations only."""
from django.shortcuts import get_object_or_404


def su_qs(user, manager, owner_field='owner'):
    """All objects for superusers; owner-filtered for everyone else."""
    if user.is_superuser:
        return manager.all()
    return manager.filter(**{owner_field: user})


def su_get(model, pk, user, owner_field='owner', **extra):
    """get_object_or_404 with superuser bypass on the owner check."""
    if user.is_superuser:
        return get_object_or_404(model, pk=pk, **extra)
    return get_object_or_404(model, pk=pk, **{owner_field: user}, **extra)
