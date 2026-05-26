from django.contrib import admin
from .models import Conversation, Message, TemplateCategory, PromptTemplate, GeneratedDocument, VoiceNote, MemoryNote


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'order', 'active']
    list_editable = ['order', 'active']


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'use_smart_model', 'order', 'active']
    list_editable = ['order', 'active', 'use_smart_model']
    list_filter = ['category', 'active']
    fieldsets = [
        (None, {'fields': ['name', 'description', 'category', 'icon', 'order', 'active']}),
        ('Prompt', {'fields': ['system_prompt', 'prompt_template', 'variables', 'use_smart_model']}),
    ]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at', 'updated_at']
    list_filter = ['user']
    raw_id_fields = ['user']


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'template', 'created_at']
    list_filter = ['user', 'template']


@admin.register(MemoryNote)
class MemoryNoteAdmin(admin.ModelAdmin):
    list_display = ['key', 'user', 'value_preview', 'updated_at']
    list_filter = ['user']
    search_fields = ['key', 'value']

    def value_preview(self, obj):
        return obj.value[:80]
    value_preview.short_description = 'Value'


@admin.register(VoiceNote)
class VoiceNoteAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user', 'transcript_preview', 'created_at', 'linked_to']
    list_filter = ['user']

    def transcript_preview(self, obj):
        return obj.transcript[:80]
    transcript_preview.short_description = 'Transcript'
