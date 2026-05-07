from django.contrib import admin
from .models import Track, TrackComment


class TrackCommentInline(admin.TabularInline):
    model = TrackComment
    extra = 0
    readonly_fields = ('user', 'timestamp_s', 'created_at')


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'bpm', 'key', 'duration_display', 'project', 'created_at')
    list_filter = ('key',)
    search_fields = ('title', 'tags')
    inlines = [TrackCommentInline]

    def duration_display(self, obj):
        return obj.duration_display()
    duration_display.short_description = 'Duration'
