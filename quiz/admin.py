from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import ExamSession, QuizAsset, QuestionQuiz



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
    list_filter = [
        "month",
        "year",
        "created_at",
        "updated_at"
    ]
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
        "image",
        "created_at",
        "updated_at",
    ]
    search_fields = [
        "id",
        "title",
    ]
    list_filter = [
        "created_at",
        "updated_at"
    ]
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


@admin.register(QuestionQuiz)
class QuestionQuizAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "type",
        "category",
        "exam_session",
        "content",
        "created_at",
        "updated_at",
        "instructions"
    ]
    search_fields = [
        "id",
        "exam_session__month",
        "exam_session__year",
        "content__prompt_text",
        "content__prompt_asset_id",
        # "content__choices__text", # not working 
    ]
    list_filter = [
        "type",
        "category",
        "exam_session",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (None, {"fields": (
            "type", "category", "exam_session",
            "instructions", "content"
        )}),
        (
            "Other information",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]