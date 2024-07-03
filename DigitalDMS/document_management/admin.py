from django.contrib import admin
from django.contrib.auth.models import Group

from .models import Document, DocumentVersion, DocumentPermission


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    pass


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    pass


@admin.register(DocumentPermission)
class DocumentPermissionAdmin(admin.ModelAdmin):
    pass
