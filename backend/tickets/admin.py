from django.contrib import admin
from .models import Ticket, DecisionLog, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'email_verified', 'created_at')
    list_filter = ('role', 'email_verified')
    list_editable = ('role',)
    search_fields = ('user__username', 'user__email')


admin.site.register(Ticket)
admin.site.register(DecisionLog)
