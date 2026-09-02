from django.contrib import admin

from .models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject

admin.site.register((SchoolYear, GradeLevel, Section, Subject, ClassSchedule))

# Register your models here.
