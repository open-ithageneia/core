from django.db import models

from open_ithageneia.managers.shared import TimeStampedQueryset


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TimeStampedQueryset.as_manager()

    class Meta:
        abstract = True


class Semester(models.Model):
    class SemesterHalf(models.IntegerChoices):
        First = 0, 'First half'
        Second = 1, 'Second half'

    year = models.PositiveSmallIntegerField()
    half = models.PositiveSmallIntegerField(choices=SemesterHalf)

    class Meta:
        unique_together = ('year', 'half')
        ordering = ['-year', '-half']
        db_table = 'semester'

    def __str__(self):
        return f"{self.get_half_display()} of {self.year}"

