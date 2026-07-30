import copy
import logging
import re
import unicodedata
import zipfile

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404, JsonResponse
from django.urls import path
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin

from open_ithageneia.utils import get_admin_image_thumb_preview

from .models import (
	DragAndDrop,
	FillInTheBlank,
	Listening,
	ListeningPart,
	MapPointer,
	Matching,
	Statement,
	QuizAsset,
	QuizCategory,
	OpenEnded,
	validate_listening_question_types,
)
from .resources import (
	FillInTheBlankResource,
	StatementResource,
	DragAndDropResource,
	MatchingResource,
	clear_image_store,
	load_images_from_zip,
	OpenEndedResource,
)
from .schemas import (
	AREA_NAME_CHOICES_BY_LEVEL,
	FillBlankText,
	MapPointerTextGroup,
)

logger = logging.getLogger(__name__)


def _fold_for_search(text: str) -> str:
	"""Lowercase and strip accents so area names match however they are typed
	(Greek is routinely typed without its tonos)."""
	stripped = "".join(
		char
		for char in unicodedata.normalize("NFD", text)
		if not unicodedata.combining(char)
	)
	return unicodedata.normalize("NFC", stripped).strip().casefold()


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


@admin.register(QuizCategory)
class QuizCategoryAdmin(admin.ModelAdmin):
	list_display = ["code", "name", "order"]
	list_editable = ["name", "order"]
	ordering = ["order", "code"]


@admin.register(QuizAsset)
class QuizAssetAdmin(ImportExportModelAdmin):
	list_display = [
		"id",
		"title",
		"image_preview",
		"image",
		"audio",
		"created_at",
		"updated_at",
	]
	search_fields = [
		"id",
		"title",
	]
	list_filter = ["created_at", "updated_at"]
	fieldsets = (
		(None, {"fields": ("title", "image", "audio")}),
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


class AbstractQuizAdmin(ZipImportMixin, ImportExportModelAdmin):
	skip_export_form = True

	list_display = [
		"id",
		"category",
		"is_active",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	search_fields = [
		"id",
	]
	list_filter = [
		"category",
		"is_active",
		"created_at",
		"updated_at",
	]
	fieldsets = (
		(None, {"fields": ("category", "is_active", "content")}),
		(
			"Other information",
			{
				"classes": ("collapse",),
				"fields": ("created_at", "updated_at"),
			},
		),
	)
	readonly_fields = ["created_at", "updated_at"]


@admin.register(Statement)
class StatementAdmin(AbstractQuizAdmin):
	resource_classes = [StatementResource]
	list_display = [
		"id",
		"type",
		"category",
		"is_active",
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
	autocomplete_fields = ["listening", "part"]
	fieldsets = (
		(
			AbstractQuizAdmin.fieldsets[0][0],
			{
				"fields": (
					"type",
					*AbstractQuizAdmin.fieldsets[0][1]["fields"],
				)
			},
		),
		(
			"Listening question",
			{
				"description": (
					"Only for statements that are part of a listening question. "
					"Edit these from the Listening page instead."
				),
				"fields": ("listening", "part", "order"),
			},
		),
		AbstractQuizAdmin.fieldsets[1],
	)
	readonly_fields = ["created_at", "updated_at"]

	@admin.display(description="Prompt preview", ordering="content__prompt_text")
	def prompt_preview(self, instance):
		prompt_text = instance.content.get("prompt_text", "")
		prompt_asset_id = instance.content.get("prompt_asset_id", None)
		prompt_audio_asset_id = instance.content.get("prompt_audio_asset_id", None)

		image_thumb_preview = get_admin_image_thumb_preview(
			instance.get_asset_image(prompt_asset_id)
		)

		audio = instance.get_asset_audio(prompt_audio_asset_id)
		audio_preview = (
			format_html('<audio controls src="{}"></audio>', audio.url) if audio else ""
		)

		if not prompt_text and not image_thumb_preview and not audio_preview:
			return None

		return format_html_join(
			"",
			'<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
			"  <span>{}</span>"
			"  <span>{}</span>"
			"  <span>{}</span>"
			"</div>",
			((prompt_text, image_thumb_preview, audio_preview),),
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


def part_position_choices(part_count):
	"""Positions a question can be assigned to: always the two parts the exam has,
	plus any further ones the group already grew."""
	return [
		(position, f"Part {position}") for position in range(1, max(2, part_count) + 1)
	]


class ListeningQuestionForm(forms.ModelForm):
	"""Picks the part by position rather than by row, so a question can be added
	in the same save as the part it belongs to — a part being created in that same
	save has no pk for a dropdown to point at yet.

	``ListeningAdmin.save_formset`` turns the position back into the ``part`` FK
	once the parts inline has been saved.
	"""

	part_position = forms.TypedChoiceField(
		coerce=int,
		choices=part_position_choices(0),
		label="Part",
		help_text=(
			"Which part above this question belongs to, counting from the top. "
			"Parts added in this same save count too."
		),
	)

	class Meta:
		model = Statement
		fields = ["order", "type", "category", "content", "is_active"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		part = self.instance.part if self.instance.part_id else None
		if part:
			self.fields["part_position"].initial = part.position


class ListeningQuestionFormSet(forms.BaseInlineFormSet):
	def clean(self):
		super().clean()
		if any(self.errors):
			return

		types = [
			form.cleaned_data["type"]
			for form in self.forms
			if form.cleaned_data and not form.cleaned_data.get("DELETE")
		]
		# An empty group is allowed so the clip can be created first and its
		# questions added on a second pass.
		if types:
			validate_listening_question_types(types)


class ListeningPartInline(admin.StackedInline):
	model = ListeningPart
	extra = 0
	fields = ["description"]
	verbose_name = "Part"
	verbose_name_plural = (
		"Parts, in order (shown as Μέρος Α, Μέρος Β, … — each with the "
		"description introducing it)"
	)


class ListeningQuestionInline(admin.StackedInline):
	model = Statement
	fk_name = "listening"
	form = ListeningQuestionForm
	formset = ListeningQuestionFormSet
	extra = 0
	ordering = ["part_id", "order", "id"]
	fields = ["part_position", "order", "type", "category", "content", "is_active"]
	verbose_name = "Question"
	verbose_name_plural = "Questions (1 True/False + N multiple choice)"

	def get_formset(self, request, obj=None, **kwargs):
		"""Offer one position per part of the group being edited. The field is
		copied first: its choices are per-group, but the declared field object is
		shared by every request."""
		formset = super().get_formset(request, obj, **kwargs)
		field = copy.deepcopy(formset.form.base_fields["part_position"])
		field.choices = part_position_choices(obj.parts.count() if obj else 0)
		formset.form.base_fields["part_position"] = field
		return formset


@admin.register(ListeningPart)
class ListeningPartAdmin(admin.ModelAdmin):
	"""Parts are normally edited inline on the listening question; this page
	exists so ``part`` can be an autocomplete field elsewhere."""

	list_display = ["id", "listening", "description", "created_at"]
	list_filter = ["created_at", "updated_at"]
	search_fields = ["id", "description", "listening__id"]
	autocomplete_fields = ["listening"]
	readonly_fields = ["created_at", "updated_at"]


@admin.register(Listening)
class ListeningAdmin(admin.ModelAdmin):
	inlines = [ListeningPartInline, ListeningQuestionInline]
	list_display = [
		"id",
		"category",
		"is_active",
		"audio_preview",
		"question_count",
		"max_plays",
		"created_at",
		"updated_at",
	]
	# Required by ``StatementAdmin.autocomplete_fields``.
	search_fields = ["id", "transcript"]
	list_filter = ["category", "is_active", "created_at", "updated_at"]
	autocomplete_fields = ["audio"]
	fields = [
		"category",
		"is_active",
		"audio",
		"max_plays",
		"transcript",
		"created_at",
		"updated_at",
	]
	readonly_fields = ["created_at", "updated_at"]

	def save_formset(self, request, form, formset, change):
		"""Point each saved question at the part whose position it picked.

		The parts inline comes first in ``inlines`` and so is saved first, which is
		what lets a part and its questions be created in the same save: by the time
		the questions are saved, the parts they refer to exist. A position with no
		part behind it grows the group an empty one, rather than leaving the
		question in no part at all and out of the exam.
		"""
		if formset.model is not Statement:
			super().save_formset(request, form, formset, change)
			return

		pending = formset.save(commit=False)
		for question_form in formset.forms:
			question = question_form.instance
			if question not in pending:
				continue
			position = question_form.cleaned_data["part_position"]
			question.part, created = ListeningPart.at_position(form.instance, position)
			if created:
				self.message_user(
					request,
					f"Part {position} did not exist yet — added it without a "
					f"description. Give it one below.",
					messages.WARNING,
				)
			question.save()

		for question in formset.deleted_objects:
			question.delete()
		formset.save_m2m()

	def get_queryset(self, request):
		return (
			super()
			.get_queryset(request)
			.select_related("audio")
			.prefetch_related("parts", "questions")
		)

	@admin.display(description="Audio")
	def audio_preview(self, instance):
		url = instance.audio_url
		return format_html('<audio controls src="{}"></audio>', url) if url else None

	@admin.display(description="Questions")
	def question_count(self, instance):
		return instance.questions.count()


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
				format_html_join(
					"",
					"<li>{}</li>",
					((item.get("text", item.get("asset_id", "")),) for item in items),
				)
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
					left_text = left_item.get("text", left_item.get("asset_id", ""))
					right_text = right_item.get("text", right_item.get("asset_id", ""))
					result_list.append(f"{left_text} → {right_text}")
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


@admin.register(OpenEnded)
class OpenEndedAdmin(AbstractQuizAdmin):
	resource_classes = [OpenEndedResource]
	list_display = [
		"id",
		"category",
		"is_active",
		"prompt_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	search_fields = AbstractQuizAdmin.search_fields + [
		"content__prompt_text",
	]

	@admin.display(description="Prompt", ordering="content__prompt_text")
	def prompt_preview(self, instance):
		prompt_text = instance.content.get("prompt_text", "")
		prompt_asset_id = instance.content.get("prompt_asset_id", None)

		image_thumb_preview = get_admin_image_thumb_preview(
			Statement.get_asset_image(prompt_asset_id)
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
		texts = instance.content.get("texts", [])
		min_correct = instance.content.get("min_correct_answers", 0)

		if not texts:
			return None

		answers = [t.get("text", "") if isinstance(t, dict) else str(t) for t in texts]

		answers_html = format_html_join(
			"",
			'<li style="margin:4px 0;">{}</li>',
			((a,) for a in answers),
		)

		return format_html(
			"""
			<div>
				<div style="margin-bottom:6px;">
					<strong>Min correct:</strong> {}
				</div>
				<ol style="margin:0;padding-left:18px;">{}</ol>
			</div>
			""",
			min_correct,
			answers_html,
		)


class MapPointerAdminForm(forms.ModelForm):
	class Meta:
		model = MapPointer
		fields = "__all__"

	class Media:
		# Ordering matters: our script must load *after* react-json-form.js
		# (which defines `reactJsonForm`) and *before* index.js (which mounts
		# the widget), so it can wrap `createForm` and capture the instance.
		js = [
			"django_jsonform/react-json-form.js",
			"quiz/map_pointer_level.js",
			"django_jsonform/index.js",
		]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# On a bound submission the dynamic `content` schema (and thus the
		# `area` enum it validates against) must reflect the level the user
		# just selected — not the saved/default level of the instance.
		# Otherwise every non-default level fails jsonform's enum validation.
		if self.is_bound and "content" in self.fields:
			raw_level = self.data.get(self.add_prefix("level"))
			if raw_level:
				try:
					self.instance.level = int(raw_level)
				except (TypeError, ValueError):
					pass
			self.fields["content"].widget.instance = self.instance


@admin.register(MapPointer)
class MapPointerAdmin(AbstractQuizAdmin):
	form = MapPointerAdminForm
	list_display = [
		"id",
		"category",
		"level",
		"is_active",
		"prompt_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	list_filter = ["level"] + AbstractQuizAdmin.list_filter
	search_fields = AbstractQuizAdmin.search_fields + [
		"content__prompt_text",
	]
	fieldsets = (
		(
			AbstractQuizAdmin.fieldsets[0][0],
			{"fields": ("level", *AbstractQuizAdmin.fieldsets[0][1]["fields"])},
		),
		AbstractQuizAdmin.fieldsets[1],
	)

	def get_urls(self):
		# Registered first so "area-options/…" is not swallowed by the admin's
		# catch-all "<path:object_id>/" route.
		return [
			path(
				"area-options/<int:level>/",
				self.admin_site.admin_view(self.area_options_view),
				name="quiz_mappointer_area_options",
			),
			*super().get_urls(),
		]

	def area_options_view(self, request, level):
		"""Options for the searchable ``areas`` picker.

		django-jsonform's autocomplete widget calls this with the typed text in
		``query`` and expects ``{"results": [...]}``. Matching ignores case and
		accents, so "ιωαννινα" finds "Ιωάννινα". A blank query lists the level's
		areas in full so the picker can also be browsed — no level runs to more
		than a few hundred names, and the popup scrolls."""
		if not self.has_view_or_change_permission(request):
			raise PermissionDenied
		names = AREA_NAME_CHOICES_BY_LEVEL.get(level)
		if names is None:
			raise Http404(f"Unknown map level: {level}")
		query = _fold_for_search(request.GET.get("query", ""))
		if query:
			names = [name for name in names if query in _fold_for_search(name)]
		return JsonResponse({"results": names})

	def get_form(self, request, obj=None, **kwargs):
		"""Bind the instance so the dynamic ``content`` schema can scope the
		area enum to the selected map level (see _map_pointer_content_schema).
		This sets the schema for the *saved* level on initial render; live
		switching is handled client-side by map_pointer_level.js."""
		form = super().get_form(request, obj, **kwargs)
		if "content" in form.base_fields:
			form.base_fields["content"].widget.instance = obj
		return form

	def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
		# Expose the per-level area names so the client-side script can rebuild
		# the `area` dropdown when the level select changes.
		extra_context = extra_context or {}
		extra_context["map_pointer_area_names"] = AREA_NAME_CHOICES_BY_LEVEL
		return super().changeform_view(request, object_id, form_url, extra_context)

	@admin.display(description="Prompt", ordering="content__prompt_text")
	def prompt_preview(self, instance):
		return instance.content.get("prompt_text", "")

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		texts = instance.content.get("texts", [])
		if not texts:
			return None

		parts = []
		for t in texts:
			if isinstance(t, dict):
				alts = t.get("alternatives", [])
				areas = MapPointerTextGroup.parse_areas(
					t["areas"] if "areas" in t else t.get("area")
				)
				parts.append((", ".join(alts), " / ".join(areas)))

		return format_html_join(
			"",
			'<div style="margin:4px 0;"><strong>{}</strong> → <code>{}</code></div>',
			parts,
		)
