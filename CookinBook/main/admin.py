from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


class AllUsersAdmin(UserAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs

    list_filter = ("is_active", "is_superuser", "groups")
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
    )


# Unregister the default User admin
admin.site.unregister(User)

# Register your customized UserAdmin
admin.site.register(User, AllUsersAdmin)
