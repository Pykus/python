# Django school journal: class and student models

This increment adds a small, reusable data-modeling exercise for a school-journal style application. It uses only synthetic data.

## Goal

Model a school class and its students with a one-to-many relationship.

```python
from django.db import models

class SchoolClass(models.Model):
    name = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.name


class Student(models.Model):
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="students",
    )
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name} {self.first_name}"
```

## Why PROTECT?

A class that still has students should not disappear accidentally. `PROTECT` makes deletion explicit instead of silently removing related records.

## Practice

1. Create migrations and migrate.
2. Add class `4A`.
3. Add three synthetic students.
4. Query `SchoolClass.objects.get(name="4A").students.filter(is_active=True)`.
5. Add a regression test proving that deleting a class with students raises `ProtectedError`.

This is a small step toward a journal-style application without copying any proprietary system.