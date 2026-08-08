from django.contrib import admin, messages
from .models import Ticket, DecisionLog, DocumentChunk, KnowledgeDocument, TicketMessage, UserProfile
from .rag import ingest_pdf


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'email_verified', 'created_at')
    list_filter = ('role', 'email_verified')
    list_editable = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    """Upload a PDF here to add it to the RAG knowledge base. Saving
    extracts, chunks and embeds it; re-uploading the same filename replaces
    its chunks."""
    list_display = ('__str__', 'category', 'chunk_count', 'uploaded_at')
    list_filter = ('category',)
    readonly_fields = ('chunk_count', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            obj.chunk_count = ingest_pdf(
                obj.file.path, document_name=str(obj), category=obj.category)
        except Exception as exc:
            obj.chunk_count = 0
            self.message_user(request, f"Ingestion failed: {exc}", level=messages.ERROR)
        else:
            if not obj.chunk_count:
                self.message_user(
                    request, "No extractable text found in this PDF.", level=messages.WARNING)
        obj.save(update_fields=['chunk_count'])

    def delete_model(self, request, obj):
        DocumentChunk.objects.filter(document_name=str(obj)).delete()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            DocumentChunk.objects.filter(document_name=str(obj)).delete()
        super().delete_queryset(request, queryset)


admin.site.register(Ticket)
admin.site.register(DecisionLog)
admin.site.register(TicketMessage)
