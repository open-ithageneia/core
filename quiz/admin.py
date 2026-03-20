import logging
import re
import zipfile

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin

from open_ithageneia.utils import get_admin_image_thumb_preview

from .forms import QuizImportForm
from .models import (
	DragAndDrop,
	ExamSession,
	FillInTheBlank,
	Matching,
	Statement,
	QuizAsset,
)
from .resources import (
	FillInTheBlankResource,
	StatementResource,
	DragAndDropResource,
	MatchingResource,
	clear_image_store,
	load_images_from_zip,
)
from .schemas import FillBlankText

logger = logging.getLogger(__name__)


class ExamSessionImportMixin:
	"""Adds an **Exam Session** dropdown to the import form.

	The selected session is forwarded to the Resource constructor via
	``get_import_resource_kwargs`` so that every imported row is
	automatically linked to it.
	"""

	import_form_class = QuizImportForm

	def get_import_resource_kwargs(self, request, **kwargs):
		rk = super().get_import_resource_kwargs(request, **kwargs)
		form = kwargs.get("form")
		if form and hasattr(form, "cleaned_data"):
			rk["exam_session"] = form.cleaned_data.get("exam_session")
		return rk


class ZipImportMixin:
	"""Accepts either a ``.zip`` or a direct spreadsheet for import.

	**ZIP upload** (existing behaviour):
	The ZIP must contain one spreadsheet file (``.xlsx``, ``.xls``, or
	``.csv``) and an optional ``images/`` folder with image files
	referenced by filename in the spreadsheet's image columns.

	**Direct spreadsheet upload** (``.xlsx`` / ``.xls`` / ``.csv``):
	When no images are bundled, users can upload a spreadsheet directly.
	Image columns should then contain existing ``QuizAsset`` IDs instead
	of filenames.

	``skip_import_confirm`` is ``True`` so images only need to be
	loaded once (no two-step confirmation).
	"""

	_SPREADSHEET_EXTENSIONS = (".xlsx", ".xls", ".csv")

	skip_import_confirm = True

	def import_action(self, request, **kwargs):
		if request.method == "POST" and request.FILES.get("import_file"):
			import_file = request.FILES["import_file"]
			name_lower = import_file.name.lower()

			if name_lower.endswith(".zip"):
				raw = b"".join(import_file.chunks())
				try:
					xlsx_bytes = load_images_from_zip(raw)
				except (zipfile.BadZipFile, ValueError):
					logger.error(
						"Failed to extract ZIP import: %s",
						import_file.name,
						exc_info=True,
					)
					clear_image_store()
					raise
				logger.info("ZIP import extracted: %s", import_file.name)
				# Replace the uploaded file with the extracted spreadsheet.
				request.FILES["import_file"] = SimpleUploadedFile(
					name="import.xlsx",
					content=xlsx_bytes,
					content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				)
			elif not any(
				name_lower.endswith(ext) for ext in self._SPREADSHEET_EXTENSIONS
			):
				from django.contrib import messages
				from django.http import HttpResponseRedirect

				messages.error(
					request,
					"Only .zip, .xlsx, .xls, or .csv files are accepted. "
					"Upload a ZIP (with images) or a spreadsheet (with asset IDs).",
				)
				return HttpResponseRedirect(request.path)
		try:
			return super().import_action(request, **kwargs)
		finally:
			clear_image_store()

	def process_import(self, request, **kwargs):
		try:
			return super().process_import(request, **kwargs)
		finally:
			clear_image_store()


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


class AbstractQuizAdmin(ExamSessionImportMixin, ZipImportMixin, ImportExportModelAdmin):
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
class StatementAdmin(AbstractQuizAdmin):
	resource_classes = [StatementResource]
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
class DragAndDropAdmin(AbstractQuizAdmin):
	resource_classes = [DragAndDropResource]

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
class MatchingAdmin(AbstractQuizAdmin):
	resource_classes = [MatchingResource]

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


@admin.register(FillInTheBlank)
class FillInTheBlankAdmin(AbstractQuizAdmin):
	resource_classes = [FillInTheBlankResource]

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		texts = instance.content.get("texts", [])

		blank_pattern = FillBlankText.BLANK_PATTERN
		choice_pattern = FillBlankText.CHOICE_PATTERN

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
