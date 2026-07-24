from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import Tag


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    search_fields = ['name']
