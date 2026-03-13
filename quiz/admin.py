from import_export import resources
import json
import re
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin

from open_ithageneia.utils import get_admin_image_thumb_preview

from .models import (
	DragAndDrop,
	ExamSession,
	FillInTheBlank,
	Matching,
	Statement,
	QuizAsset,
)


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


class AbstractQuizAdmin(admin.ModelAdmin):
	"""
	Base admin for models inheriting AbstractQuiz.
	"""

	list_display = [
		"id",
		"category",
		"get_exam_sessions_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	search_fields = [
		"id",
		"exam_sessions__month",
		"exam_sessions__year",
	]
	list_filter = [
		"category",
		"exam_sessions",
		"created_at",
		"updated_at",
	]
	fieldsets = (
		(None, {"fields": ("category", "exam_sessions", "content")}),
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
	def get_exam_sessions_preview(self, obj):
		return obj.exam_sessions_preview


@admin.register(Statement)
class StatementAdmin(AbstractQuizAdmin, ImportExportModelAdmin):
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
	search_fields = AbstractQuizAdmin.search_fields + [
		"content__prompt_text",
		"content__prompt_asset_id",
		# "content__choices__text", # not working, TODO: Check it
	]
	list_filter = ["type"] + AbstractQuizAdmin.list_filter
	fieldsets = (
		(
			AbstractQuizAdmin.fieldsets[0][0],
			{"fields": ("type", *AbstractQuizAdmin.fieldsets[0][1]["fields"])},
		),
		AbstractQuizAdmin.fieldsets[1],
	)
	readonly_fields = ["created_at", "updated_at"]

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

	@admin.display(description="Answer")
	def answer_preview(self, instance):
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


@admin.register(DragAndDrop)
class DragAndDropAdmin(AbstractQuizAdmin, ImportExportModelAdmin):
	@admin.display(description="Answer")
	def answer_preview(self, instance):
		content = getattr(instance, "content", [])

		if not isinstance(content, list) or len(content) != 2:
			return format_html(
				"<em>Invalid content shape (expected 2 columns).</em>", None
			)

		def render_col(col):
			title = col.get("title", "")
			values = col.get("values", [])

			items_html = (
				format_html_join("", "<li>{}</li>", ((v,) for v in values))
				if isinstance(values, list)
				else ""
			)

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


@admin.register(Matching)
class MatchingAdmin(AbstractQuizAdmin, ImportExportModelAdmin):
	@admin.display(description="Answer")
	def answer_preview(self, instance):
		content = getattr(instance, "content", [])

		if not isinstance(content, list) or len(content) != 2:
			return format_html(
				"<em>Invalid content shape (expected 2 columns).</em>", None
			)

		def render_col(col, list_type="1"):
			title = col.get("title", "")
			items = col.get("items", [])

			items_html = (
				format_html_join("", "<li>{}</li>", ((item["text"],) for item in items))
				if isinstance(items, list)
				else ""
			)

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
				items,
			]

		[left_html, left_items] = render_col(instance.content[0])
		[right_html, right_items] = render_col(instance.content[1], list_type="A")

		result_list = []

		for left_item in left_items:
			for right_item in right_items:
				if left_item.get("id", None) == right_item.get("matched_id", None):
					result_list.append(f"{left_item['text']} → {right_item['text']}")
					break

		result_list_html = (
			format_html_join(
				"", "<p><em>{}</em></p>", ((result,) for result in result_list)
			)
			if isinstance(result_list, list)
			else ""
		)

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
			result_list_html,
		)


class FillInTheBlankResource(resources.ModelResource):
	class Meta:
		model = FillInTheBlank
		fields = ("id", "category", "content")
		import_id_fields = ("id",)

	def before_import_row(self, row, row_number=None, **kwargs):
		"""Assemble content JSON from flat xlsx columns."""
		texts = []
		i = 1
		while f"text_{i}" in row and row[f"text_{i}"]:
			texts.append({"text": row[f"text_{i}"]})
			i += 1

		row["content"] = json.dumps(
			{
				"show_answers_as_choices": str(
					row.get("show_answers_as_choices", "false")
				).lower()
				== "true",
				"prompt_asset_id": int(row["prompt_asset_id"])
				if row.get("prompt_asset_id")
				else None,
				"texts": texts,
			}
		)


@admin.register(FillInTheBlank)
class FillInTheBlankAdmin(AbstractQuizAdmin, ImportExportModelAdmin):
	resource_classes = [FillInTheBlankResource]

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		texts = instance.content.get("texts", [])

		blank_pattern = FillInTheBlank.BLANK_PATTERN
		choice_pattern = FillInTheBlank.CHOICE_PATTERN

		def get_correct_answer(blank_content: str) -> str:
			choices = choice_pattern.findall(blank_content)
			correct = [text for text, marker in choices if marker == "*"]
			return correct[0] if correct else "?"

		def get_all_choices(blank_content: str) -> list[str]:
			return [text for text, _ in choice_pattern.findall(blank_content)]

		def render_text(text: str) -> str:
			split_pattern = re.compile(r"<.+?>")
			parts = split_pattern.split(text)
			blanks = blank_pattern.findall(text)
			out = []
			for i, chunk in enumerate(parts):
				out.append(format_html("{}", chunk))
				if i < len(blanks):
					correct = get_correct_answer(blanks[i])
					all_choices = get_all_choices(blanks[i])
					out.append(
						format_html(
							"<u><strong>{}</strong></u> ({})",
							correct,
							", ".join(all_choices),
						)
					)
			return mark_safe("".join(str(x) for x in out))

		all_correct = [
			get_correct_answer(blank)
			for t in texts
			for blank in blank_pattern.findall(t.get("text", ""))
		]

		rendered_texts = [render_text(t.get("text", "")) for t in texts]
		rendered_html_list = format_html_join(
			"", "<p>{}</p>", ((html,) for html in rendered_texts)
		)

		return format_html(
			"""
			<div>
				<p><em>{}</em></p>
			</div>
			<div style="margin-top: 10px;">
				{}
			</div>
			""",
			", ".join(all_correct),
			rendered_html_list,
		)
