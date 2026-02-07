from django.contrib import admin
from django.utils.html import format_html_join
from import_export.admin import ImportExportModelAdmin

from .models import ExamSession, QuizAsset, Quiz
from open_ithageneia.utils import get_admin_image_thumb_preview


@admin.register(ExamSession)
class ExamSessionAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "month",
        "year",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "id",
        "month",
        "year",
    ]
    list_filter = ["month", "year", "created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("month", "year")}),
        (
            "Other information",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]


@admin.register(QuizAsset)
class QuizAssetAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "title",
        "image_preview",
        "image",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "id",
        "title",
    ]
    list_filter = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("title", "image")}),
        (
            "Other information",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Image preview")
    def image_preview(self, obj):
        return get_admin_image_thumb_preview(obj.image)


@admin.register(Quiz)
class QuizAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "type",
        "category",
        "get_exam_sessions_preview",
        "prompt_preview",
        "choices_preview",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "id",
        "exam_sessions__month",
        "exam_sessions__year",
        "content__prompt_text",
        "content__prompt_asset_id",
        # "content__choices__text", # not working, TODO: Check it
    ]
    list_filter = [
        "type",
        "category",
        "exam_sessions",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (None, {"fields": ("type", "category", "exam_sessions", "content")}),
        (
            "Other information",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Exam sessions preview", ordering="exam_sessions__year")
    def get_exam_sessions_preview(self, instance):
        return instance.exam_sessions_preview

    @admin.display(description="Prompt preview", ordering="content__prompt_text")
    def prompt_preview(self, instance):
        prompt_text = instance.content.get("prompt_text", "")
        prompt_asset_id = instance.content.get("prompt_asset_id", None)

        image_thumb_preview = get_admin_image_thumb_preview(
            instance.get_asset_image(prompt_asset_id)
        )

        if not prompt_text and not image_thumb_preview:
            return None

        return format_html_join(
            "",
            '<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
            "  <span>{}</span>"
            "  <span>{}</span>"
            "</div>",
            ((prompt_text, image_thumb_preview),),
        )

    @admin.display(description="Choices")
    def choices_preview(self, instance):
        choices = instance.get_choices_with_images()

        if not choices:
            return None

        return format_html_join(
            "",
            '<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
            '  <span style="width:20px">{}</span>'
            "  <span>{}</span>"
            "  <span>{}</span>"
            "</div>",
            (
                (
                    "✅" if bool(choice.get("is_correct")) else "◻️",
                    choice.get("text", ""),
                    get_admin_image_thumb_preview(choice.get("image", None)),
                )
                for choice in choices
            ),
        )
