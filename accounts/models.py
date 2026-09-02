from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'
        PARENT = 'PARENT', 'Parent/Guardian'
        GUIDANCE = 'GUIDANCE', 'Guidance Personnel'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)

    def __str__(self):
        return self.get_full_name() or self.username

# Create your models here.
