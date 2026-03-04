from django.db import models

from .managers import TimeStampedQueryset, ActivatableQuerySet


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TimeStampedQueryset.as_manager()

    class Meta:
        abstract = True


class ActivatableModel(models.Model):
    is_active = models.BooleanField(default=True)

    objects = ActivatableQuerySet.as_manager()

    class Meta:
        abstract = True
