from django.db.models.query import QuerySet
from django.utils import timezone


class TimeStampedQueryset(QuerySet):

    def update(self, **kwargs):
        # Also runs for bulk_update (https://docs.djangoproject.com/en/6.0/ref/models/querysets/#bulk-update)

        kwargs["date_updated"] = timezone.now()

        return super().update(**kwargs)


class ActivatableQuerySet(QuerySet):

    def active(self):
        return self.filter(is_active=True)