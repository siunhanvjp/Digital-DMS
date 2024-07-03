from django.contrib import admin
from django.contrib.auth.models import Group

from .models import User


# Unregister the Group model from admin.
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass
