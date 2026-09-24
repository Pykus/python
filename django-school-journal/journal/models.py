"""Core data model for a small school journal.

The project is intentionally generic and uses fictional domain names. It is inspired by
common electronic school-journal workflows, not by any proprietary implementation.
"""

from django.db import models


class SchoolClass(models.Model):
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ("code",)
        verbose_name_plural = "school classes"

    def __str__(self) -> str:
        return self.code


class Student(models.Model):
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="students",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = [
            models.Index(fields=("school_class", "last_name", "first_name")),
        ]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name}"


class Subject(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Lesson(models.Model):
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="lessons",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="lessons",
    )
    starts_at = models.DateTimeField(db_index=True)
    topic = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-starts_at",)

    def __str__(self) -> str:
        return f"{self.school_class} / {self.subject} / {self.starts_at:%Y-%m-%d %H:%M}"


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="attendance",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("lesson", "student"),
                name="unique_attendance_per_lesson_student",
            ),
        ]
        indexes = [
            models.Index(fields=("student", "status")),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.lesson} - {self.get_status_display()}"
