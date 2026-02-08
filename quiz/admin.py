from django.contrib import admin
from django.utils.html import format_html, format_html_join
from import_export.admin import ImportExportModelAdmin

from open_ithageneia.utils import get_admin_image_thumb_preview
from .models import ExamSession, QuizAsset, Quiz
from .schemas import get_quiz_schema, SCHEMA_BY_TYPE, DEFAULT_SCHEMA
from .constants import QuizType


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
        "answer_preview",
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


    def get_form(self, request, instance=None, **kwargs):
        form = super().get_form(request, instance, **kwargs)

        if instance is None:
            quiz_type = request.GET.get("type", QuizType.TRUE_FALSE)

            schema = SCHEMA_BY_TYPE.get(quiz_type, DEFAULT_SCHEMA)
        else:
            schema = get_quiz_schema(instance)

        if "content" in form.base_fields:
            form.base_fields["content"].widget.schema = schema

        return form

    @admin.display(description="Exam sessions preview", ordering="exam_sessions__year")
    def get_exam_sessions_preview(self, instance):
        return instance.exam_sessions_preview

    @admin.display(description="Prompt preview", ordering="content__prompt_text")
    def prompt_preview(self, instance):
        if instance.type in [QuizType.TRUE_FALSE, QuizType.MULTIPLE_CHOICE]:
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
        
        if instance.type in [QuizType.DRAG_AND_DROP, QuizType.MATCHING]:
            return None
        
        return None

    @admin.display(description="Answer")
    def answer_preview(self, instance):
        if instance.type in [QuizType.TRUE_FALSE, QuizType.MULTIPLE_CHOICE]:
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

        if instance.type == QuizType.DRAG_AND_DROP:
            content = getattr(instance, "content", [])

            if not isinstance(content, list) or len(content) != 2:
                return format_html("<em>Invalid content shape (expected 2 columns).</em>", None)
            
            def render_col(col):
                title = col.get("title", "")
                values = col.get("values", [])

                items_html = format_html_join(
                    "", "<li>{}</li>", ((v,) for v in values)
                ) if isinstance(values, list) else ""

                return format_html(
                    """
                    <div style="
                        flex: 1;
                        padding: 12px;
                        border: 1px solid #e6e6fa;
                        border-radius: 8px;
                    ">
                        <div style="font-weight: 600; margin-bottom: 8px;">{}</div>
                        <ul style="margin: 0; padding-left: 18px;">{}</ul>
                    </div>
                    """,
                    title,
                    items_html,
                )

            left_html = render_col(instance.content[0])
            right_html = render_col(instance.content[1])

            return format_html(
                """
                <div style="display:flex; gap: 12px; align-items: flex-start; max-width: 900px;">
                    {} {}
                </div>
                """,
                left_html,
                right_html,
            )
        
        if instance.type == QuizType.MATCHING:
            content = getattr(instance, "content", [])

            if not isinstance(content, list) or len(content) != 2:
                return format_html("<em>Invalid content shape (expected 2 columns).</em>", None)
            
            def render_col(col, list_type="1"):
                title = col.get("title", "")
                items = col.get("items", [])

                items_html = format_html_join(
                    "", "<li>{}</li>", ((item["text"],) for item in items)
                ) if isinstance(items, list) else ""

                return [
                    format_html(
                        """
                        <div style="
                            flex: 1;
                            padding: 12px;
                            border: 1px solid #e6e6fa;
                            border-radius: 8px;
                        ">
                            <div style="font-weight: 600; margin-bottom: 8px;">{}</div>
                            <ol type="{}" style="margin: 0; padding-left: 18px;">{}</ol>
                        </div>
                        """,
                        title,
                        list_type,
                        items_html,
                    ),
                    items
                ]

            [left_html, left_items] = render_col(instance.content[0])
            [right_html, right_items] = render_col(instance.content[1], list_type="A")

            result_list = []

            for left_item in left_items:
                for right_item in right_items:
                    if left_item.get("id", None) == right_item.get("matched_id", None):
                        result_list.append(f"{left_item["text"]} → {right_item["text"]}")
                        break

            result_list_html = format_html_join(
                "", "<p><em>{}</em></p>", ((result,) for result in result_list)
            ) if isinstance(result_list, list) else ""

            return format_html(
                """
                <div style="display:flex; gap: 12px; align-items: flex-start; max-width: 900px;">
                    {} {}
                </div>
                <div style="margin-top: 10px;">
                    {}
                </div>
                """,
                left_html,
                right_html,
                result_list_html
            )
        
        return None
        
    class Media:
        js = ("admin/quiz_schema_switch.js",)
