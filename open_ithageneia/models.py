from django.db import models
from .managers.py import TimeStampedQueryset


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TimeStampedQueryset.as_manager()

    class Meta:
        abstract = True
