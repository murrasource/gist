from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from mailserver.models import User, Account, VirtualDomain, VirtualUser, VirtualAlias

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'is_staff', 'is_active',)
    list_filter = ('email', 'is_staff', 'is_active',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email',)
    ordering = ('email',)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'dob']

@admin.register(VirtualDomain)
class VirutalDomainAdmin(admin.ModelAdmin):
    list_display = ['id', 'name',]

@admin.register(VirtualUser)
class VirtualUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'password', 'quota']

@admin.register(VirtualAlias)
class VirtualAliasAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'destination']