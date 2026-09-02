from django.contrib import admin

from .models import Enrollment, Guardian, Student, StudentGuardian

admin.site.register((Student, Guardian, StudentGuardian, Enrollment))

# Register your models here.
