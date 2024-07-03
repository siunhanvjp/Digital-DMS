from django.contrib import admin
from django.contrib.auth.models import Group

from .models import EntryLogs


@admin.register(EntryLogs)
class EntryLogsAdmin(admin.ModelAdmin):
    pass
