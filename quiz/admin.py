import copy
import logging
import zipfile

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin

from open_ithageneia.utils import get_admin_image_thumb_preview

from .models import (
	DragAndDrop,
	DragAndDropValue,
	FillInTheBlank,
	FillInTheBlankExtraChoice,
	FillInTheBlankText,
	Listening,
	ListeningPart,
	MapArea,
	MapPointer,
	MapPointerAlternative,
	MapPointerAnswer,
	MapPointerAnswerArea,
	Matching,
	MatchPair,
	OpenEnded,
	OpenEndedAlternative,
	OpenEndedAnswer,
	QuizAsset,
	QuizCategory,
	Statement,
	StatementChoice,
	validate_listening_question_types,
)
from .resources import (
	DragAndDropResource,
	FillInTheBlankResource,
	MatchingResource,
	OpenEndedResource,
	StatementResource,
	clear_image_store,
	load_images_from_zip,
)

logger = logging.getLogger(__name__)


def without_category(fields):
	"""``fields`` minus ``category``.

	Some quiz types only ever belong to one category, so on their pages the
	picker, the column and the filter are all noise. See
	``FixedCategoryFormMixin`` for how the value gets set once the field is gone.
	"""
	return [field for field in fields if field != "category"]


class FixedCategoryFormMixin:
	"""Stamps ``fixed_category`` on the instance being saved, for the admin pages
	that leave ``category`` out of their fields.

	The stamp has to happen here rather than through a model default: a field the
	admin does not render is one nothing fills in, and the value is a property of
	the page (a listening question is a listening question) rather than of the
	table. Setting it on ``self.instance`` — not as form ``initial``, which only
	feeds rendered fields — puts it in place before validation, and Django's
	``_post_clean`` leaves fields the form does not carry alone, so it survives to
	the save.
	"""

	fixed_category = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.instance.category_id = self.fixed_category


class LinesField(forms.CharField):
	"""A textarea holding one item per line.

	The types that accept a written answer store each alternative spelling as its
	own row, but authors think of them as a short list they type out. The rows
	stay the storage; this is only how they are edited.
	"""

	widget = forms.Textarea(attrs={"rows": 3, "cols": 60})

	def clean(self, value):
		value = super().clean(value)
		return [line.strip() for line in (value or "").splitlines() if line.strip()]


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
	list_display = ["code", "name", "name_el", "order"]
	list_editable = ["name", "name_el", "order"]
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


@admin.register(MapArea)
class MapAreaAdmin(admin.ModelAdmin):
	"""Read-only on purpose.

	Rows are generated from the GeoJSON by ``manage.py sync_map_areas``, and the
	name has to stay byte-identical to the property the client matches against —
	editing one here would break the match silently. The registration exists so
	the answer picker can autocomplete against it.
	"""

	list_display = ["name", "level", "answer_count"]
	list_filter = ["level"]
	search_fields = ["name", "search_name"]
	ordering = ["level", "name"]

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False

	def get_queryset(self, request):
		# ``answer_count`` is a column on a changelist that pages 100 rows at a
		# time, and level 4 is every municipality in the country — counting per
		# row is 100 extra queries a page.
		return (
			super().get_queryset(request).annotate(_answer_count=Count("answer_links"))
		)

	@admin.display(description="Answers using it")
	def answer_count(self, instance):
		return instance._answer_count


class AbstractQuizAdmin(ZipImportMixin, ImportExportModelAdmin):
	skip_export_form = True

	# The question itself. Types that ask it differently — ``DragAndDrop`` asks
	# nothing, ``Listening`` asks with a clip — override this.
	prompt_fields = ("prompt_text",)

	list_display = [
		"id",
		"category",
		"test_number",
		"question_number",
		"is_active",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	search_fields = [
		"id",
		"test_number",
		"question_number",
	]
	list_filter = [
		"category",
		"test_number",
		"question_number",
		"is_active",
		"created_at",
		"updated_at",
	]
	readonly_fields = ["created_at", "updated_at"]

	@classmethod
	def base_fieldsets(cls, *, extra_fields=(), prompt_fields=None, category=True):
		"""The shared page layout, with each type's own fields folded in.

		Built rather than written out because every quiz admin wants the same
		three sections in the same order and differs only in what goes into the
		first one.
		"""
		fields = ["category"] if category else []
		fields += ["test_number", "question_number", "is_active"]
		fields += list(extra_fields)
		prompt = list(cls.prompt_fields if prompt_fields is None else prompt_fields)
		sections = [(None, {"fields": tuple(fields)})]
		if prompt:
			sections.append(("Question", {"fields": tuple(prompt)}))
		sections.append(
			(
				"Other information",
				{
					"classes": ("collapse",),
					"fields": ("created_at", "updated_at"),
				},
			)
		)
		return tuple(sections)

	def get_queryset(self, request):
		# The list page renders every question's answer, so the rows it is built
		# from are worth fetching up front rather than one query per question.
		qs = super().get_queryset(request)
		related = getattr(self, "list_prefetch", ())
		return qs.prefetch_related(*related) if related else qs


class StatementChoiceFormSet(forms.BaseInlineFormSet):
	"""Repeats ``Statement._validate_content`` for admin saves.

	The rule counts choices, and the admin saves the question before its inlines,
	so the model check cannot see them on a create. This is where it bites.
	"""

	def clean(self):
		super().clean()
		if any(self.errors):
			return

		live = [
			form.cleaned_data
			for form in self.forms
			if form.cleaned_data and not form.cleaned_data.get("DELETE")
		]
		if self.instance.type != Statement.StatementType.MULTIPLE_CHOICE:
			return

		# Deliberately no early return on an empty ``live``: marking every choice
		# for deletion has to fail here as well. The model rule reads rows the
		# admin only writes after the parent is saved, so an emptied
		# multiple-choice question would otherwise save cleanly and be served
		# with nothing to choose from.
		if not any(choice.get("is_correct") for choice in live):
			raise forms.ValidationError(
				"Multiple-choice questions must have at least one correct choice."
			)


class StatementChoiceInline(admin.TabularInline):
	model = StatementChoice
	formset = StatementChoiceFormSet
	extra = 0
	fields = ["order", "text", "image", "is_correct"]
	autocomplete_fields = ["image"]
	ordering = ["order", "id"]


@admin.register(Statement)
class StatementAdmin(AbstractQuizAdmin):
	resource_classes = [StatementResource]
	inlines = [StatementChoiceInline]
	prompt_fields = ("prompt_text", "prompt_image", "prompt_audio")
	list_prefetch = ("choices__image", "prompt_image", "prompt_audio")
	list_display = [
		"id",
		"type",
		"category",
		"test_number",
		"question_number",
		"is_active",
		"prompt_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	# A real column and a real join: searching choice text used to be impossible
	# through the JSON blob and carried a TODO saying so.
	search_fields = AbstractQuizAdmin.search_fields + [
		"prompt_text",
		"choices__text",
	]
	list_filter = ["type"] + AbstractQuizAdmin.list_filter
	autocomplete_fields = ["listening", "part", "prompt_image", "prompt_audio"]
	readonly_fields = ["created_at", "updated_at"]

	def get_fieldsets(self, request, obj=None):
		return self.base_fieldsets(extra_fields=("type",))[:1] + (
			(
				"Question",
				{"fields": ("prompt_text", "prompt_image", "prompt_audio")},
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
			(
				"Other information",
				{
					"classes": ("collapse",),
					"fields": ("created_at", "updated_at"),
				},
			),
		)

	@admin.display(description="Prompt preview", ordering="prompt_text")
	def prompt_preview(self, instance):
		image_thumb_preview = get_admin_image_thumb_preview(
			instance.prompt_image.image if instance.prompt_image else None
		)

		audio = instance.prompt_audio.audio if instance.prompt_audio else None
		audio_preview = (
			format_html('<audio controls src="{}"></audio>', audio.url) if audio else ""
		)

		if not instance.prompt_text and not image_thumb_preview and not audio_preview:
			return None

		return format_html_join(
			"",
			'<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
			"  <span>{}</span>"
			"  <span>{}</span>"
			"  <span>{}</span>"
			"</div>",
			((instance.prompt_text, image_thumb_preview, audio_preview),),
		)

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		choices = list(instance.choices.all())

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
					"✅" if choice.is_correct else "◻️",
					choice.text,
					get_admin_image_thumb_preview(
						choice.image.image if choice.image else None
					),
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


class ListeningQuestionForm(FixedCategoryFormMixin, forms.ModelForm):
	"""Picks the part by position rather than by row, so a question can be added
	in the same save as the part it belongs to — a part being created in that same
	save has no pk for a dropdown to point at yet.

	``ListeningAdmin.save_formset`` turns the position back into the ``part`` FK
	once the parts inline has been saved.

	A question asked about a clip is part of the listening section whatever
	subject the clip covers, so it is categorised as such and the picker is left
	off the inline.
	"""

	fixed_category = QuizCategory.LISTENING

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
		fields = ["order", "type", "prompt_text", "is_active"]

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
	fields = [
		"part_position",
		"order",
		"type",
		"prompt_text",
		"choices_summary",
		"is_active",
	]
	readonly_fields = ["choices_summary"]
	verbose_name = "Question"
	verbose_name_plural = "Questions (1 True/False + N multiple choice)"

	@admin.display(description="Choices")
	def choices_summary(self, instance):
		"""The question's choices, with a link to where they can be edited.

		Choices are rows on the statement, and a statement is already an inline
		here — Django does not do inlines inside inlines, so they are listed
		read-only and edited on the statement's own page.
		"""
		if not instance.pk:
			return "Save the question first, then add its choices."
		choices = list(instance.choices.all())
		listed = (
			format_html_join(
				"",
				"<li>{} {}</li>",
				(
					("✅" if choice.is_correct else "◻️", choice.text)
					for choice in choices
				),
			)
			if choices
			else mark_safe("<li><em>none yet</em></li>")
		)
		return format_html(
			'<ul style="margin:0;padding-left:18px;">{}</ul>'
			'<a href="{}" target="_blank">Edit choices →</a>',
			listed,
			reverse("admin:quiz_statement_change", args=[instance.pk]),
		)

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
	"""Parts are edited inline on the listening question. This registration exists
	only so ``part`` can be an autocomplete field on ``StatementAdmin``: the
	autocomplete endpoint looks its target up in the admin registry and 404s
	unless that admin declares ``search_fields``. The page itself is hidden and
	read-only, so the inline stays the one way in.

	``has_view_permission`` is left alone — autocomplete permission-checks against
	it. None of this reaches ``ListeningPartInline``, whose permissions are
	checked on the inline class rather than here.
	"""

	search_fields = ["id", "description", "listening__id"]

	def get_model_perms(self, request):
		return {}

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


class ListeningForm(FixedCategoryFormMixin, forms.ModelForm):
	"""Every clip belongs to the listening section, so the category is stamped on
	rather than picked."""

	fixed_category = QuizCategory.LISTENING

	class Meta:
		model = Listening
		fields = "__all__"


@admin.register(Listening)
class ListeningAdmin(admin.ModelAdmin):
	form = ListeningForm
	inlines = [ListeningPartInline, ListeningQuestionInline]
	list_display = [
		"id",
		"test_number",
		"question_number",
		"is_active",
		"audio_preview",
		"question_count",
		"max_plays",
		"created_at",
		"updated_at",
	]
	# Required by ``StatementAdmin.autocomplete_fields``.
	search_fields = ["id", "test_number", "question_number", "transcript"]
	list_filter = [
		"test_number",
		"question_number",
		"is_active",
		"created_at",
		"updated_at",
	]
	autocomplete_fields = ["audio"]
	fields = [
		"test_number",
		"question_number",
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
			.prefetch_related("parts", "questions__choices")
		)

	@admin.display(description="Audio")
	def audio_preview(self, instance):
		url = instance.audio_url
		return format_html('<audio controls src="{}"></audio>', url) if url else None

	@admin.display(description="Questions")
	def question_count(self, instance):
		return instance.questions.count()


class DragAndDropValueInline(admin.TabularInline):
	model = DragAndDropValue
	extra = 0
	fields = ["side", "order", "text"]
	ordering = ["side", "order", "id"]


@admin.register(DragAndDrop)
class DragAndDropAdmin(AbstractQuizAdmin):
	resource_classes = [DragAndDropResource]
	inlines = [DragAndDropValueInline]
	# The question is the two columns themselves — there is no prompt.
	prompt_fields = ()
	list_prefetch = ("values",)

	def get_fieldsets(self, request, obj=None):
		return self.base_fieldsets(extra_fields=("left_title", "right_title"))

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		values = list(instance.values.all())

		def render_col(title, side):
			items_html = format_html_join(
				"",
				"<li>{}</li>",
				((value.text,) for value in values if value.side == side),
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

		return format_html(
			"""
            <div style="display:flex; gap: 12px; align-items: flex-start; max-width: 900px;">
                {} {}
            </div>
            """,
			render_col(instance.left_title, DragAndDropValue.Side.LEFT),
			render_col(instance.right_title, DragAndDropValue.Side.RIGHT),
		)


class MatchPairInline(admin.TabularInline):
	model = MatchPair
	extra = 0
	fields = [
		"order",
		"left_text",
		"left_image",
		"right_order",
		"right_text",
		"right_image",
	]
	autocomplete_fields = ["left_image", "right_image"]
	ordering = ["order", "id"]
	verbose_name = "Pair"
	verbose_name_plural = (
		"Pairs — one row is one matching. 'Order' places the left item, "
		"'right order' the right one: give them different orders to stop the "
		"right column running parallel to the left."
	)


@admin.register(Matching)
class MatchingAdmin(AbstractQuizAdmin):
	resource_classes = [MatchingResource]
	inlines = [MatchPairInline]
	list_prefetch = ("pairs__left_image", "pairs__right_image")

	def get_fieldsets(self, request, obj=None):
		return self.base_fieldsets(extra_fields=("left_title", "right_title"))

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		pairs = list(instance.pairs.all())
		# The two columns are ordered independently, so the right one is sorted
		# the way the serializer sorts it. Drawing both in left order would show
		# a page the candidate never sees — and a shuffled right column is the
		# whole point of ``right_order``.
		# A row missing a side has no item in that column; see ``MatchPair``.
		left_sequence = [pair for pair in pairs if pair.has_left]
		right_sequence = sorted(
			(pair for pair in pairs if pair.has_right),
			key=lambda pair: (pair.right_order, pair.order, pair.pk),
		)

		def label(text, image):
			return text or (image.title if image else "")

		def render_col(title, list_type, sequence, side):
			items_html = format_html_join(
				"",
				"<li>{}</li>",
				(
					(
						label(pair.left_text, pair.left_image)
						if side == "left"
						else label(pair.right_text, pair.right_image),
					)
					for pair in sequence
				),
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
                    <ol type="{}" style="margin: 0; padding-left: 18px;">{}</ol>
                </div>
                """,
				title,
				list_type,
				items_html,
			)

		# The row is the pairing, so this no longer has to reconstruct it by
		# matching ids across the two columns.
		result_list_html = format_html_join(
			"",
			"<p><em>{} → {}</em></p>",
			(
				(
					label(pair.left_text, pair.left_image),
					label(pair.right_text, pair.right_image),
				)
				for pair in pairs
			),
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
			render_col(instance.left_title, "1", left_sequence, "left"),
			render_col(instance.right_title, "A", right_sequence, "right"),
			result_list_html,
		)


class FillInTheBlankTextInline(admin.TabularInline):
	model = FillInTheBlankText
	extra = 0
	fields = ["order", "text"]
	ordering = ["order", "id"]
	verbose_name = "Sentence"
	verbose_name_plural = (
		"Sentences — mark blanks as <{{answer}}*>, with * on the correct choice"
	)


class FillInTheBlankExtraChoiceInline(admin.TabularInline):
	model = FillInTheBlankExtraChoice
	extra = 0
	fields = ["order", "text"]
	ordering = ["order", "id"]
	verbose_name = "Extra choice"
	verbose_name_plural = "Extra choices (distractors shown in the word bank)"


@admin.register(FillInTheBlank)
class FillInTheBlankAdmin(AbstractQuizAdmin):
	resource_classes = [FillInTheBlankResource]
	inlines = [FillInTheBlankTextInline, FillInTheBlankExtraChoiceInline]
	prompt_fields = ("prompt_image",)
	autocomplete_fields = ["prompt_image"]
	list_prefetch = ("texts__parts__choices", "extra_choices", "prompt_image")

	def get_fieldsets(self, request, obj=None):
		return self.base_fieldsets(extra_fields=("show_answers_as_choices",))

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		sentences = list(instance.texts.all())

		def render(sentence):
			"""The sentence with each blank's answer underlined in place.

			Built from the derived rows rather than from the markup, so the page
			also shows whether they actually got derived.
			"""
			out = []
			for part in sentence.parts.all():
				if not part.is_blank:
					out.append(format_html("{}", part.text))
					continue
				choices = list(part.choices.all())
				correct = next(
					(choice.text for choice in choices if choice.is_correct), "?"
				)
				out.append(
					format_html(
						"<u><strong>{}</strong></u> ({})",
						correct,
						", ".join(choice.text for choice in choices),
					)
				)
			return mark_safe("".join(str(part) for part in out))

		all_correct = [
			choice.text
			for sentence in sentences
			for part in sentence.parts.all()
			for choice in part.choices.all()
			if choice.is_correct
		]

		rendered_html_list = format_html_join(
			"", "<p>{}</p>", ((render(sentence),) for sentence in sentences)
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


class AlternativesInlineForm(forms.ModelForm):
	"""Edits an answer's alternative spellings as a block of lines.

	``alternatives`` are rows on their own table, but a nested inline is not a
	thing Django does — and typing them one per line is how an author thinks of
	them anyway.
	"""

	alternatives_text = LinesField(
		label="Alternatives",
		required=True,
		help_text="One spelling or phrasing per line. All of them count as correct.",
	)

	#: set by each subclass — the model holding one alternative.
	alternative_model = None

	class Meta:
		fields = ["order"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.instance.pk:
			self.fields["alternatives_text"].initial = "\n".join(
				self.instance.alternatives.values_list("text", flat=True)
			)

	def save(self, commit=True):
		answer = super().save(commit=commit)
		if commit:
			self._save_alternatives(answer)
		else:
			# The formset saves the row itself; hook the children onto that.
			original_save_m2m = getattr(self, "save_m2m", None)

			def save_m2m():
				if original_save_m2m:
					original_save_m2m()
				self._save_alternatives(answer)

			self.save_m2m = save_m2m
		return answer

	def _save_alternatives(self, answer):
		# Replace wholesale: the textarea is the whole list, so anything missing
		# from it was removed.
		answer.alternatives.all().delete()
		self.alternative_model.objects.bulk_create(
			[
				self.alternative_model(answer=answer, text=text, order=index)
				for index, text in enumerate(self.cleaned_data["alternatives_text"])
			]
		)


class OpenEndedAnswerForm(AlternativesInlineForm):
	alternative_model = OpenEndedAlternative

	class Meta(AlternativesInlineForm.Meta):
		model = OpenEndedAnswer


class MinCorrectAnswersFormSet(forms.BaseInlineFormSet):
	"""Repeats ``MinCorrectAnswersMixin._validate_min_correct_answers`` for admin
	saves.

	The rule counts the question's answers, and the admin saves the question
	before its inlines — on a create there are none to count, so the model check
	waves through any number at all.
	"""

	def clean(self):
		super().clean()
		if any(self.errors):
			return

		live = [
			form
			for form in self.forms
			if form.cleaned_data and not form.cleaned_data.get("DELETE")
		]
		# An answerless question is allowed, the same way the model rule allows
		# one: the answers can be added on a second pass.
		if not live:
			return

		minimum = self.instance.min_correct_answers
		if minimum > len(live):
			raise forms.ValidationError(
				f"min_correct_answers ({minimum}) cannot exceed the number of "
				f"available answers ({len(live)})."
			)


class OpenEndedAnswerInline(admin.TabularInline):
	model = OpenEndedAnswer
	form = OpenEndedAnswerForm
	formset = MinCorrectAnswersFormSet
	extra = 0
	fields = ["order", "alternatives_text"]
	ordering = ["order", "id"]
	verbose_name = "Accepted answer"
	verbose_name_plural = "Accepted answers"


@admin.register(OpenEnded)
class OpenEndedAdmin(AbstractQuizAdmin):
	resource_classes = [OpenEndedResource]
	inlines = [OpenEndedAnswerInline]
	prompt_fields = ("prompt_text", "prompt_image")
	autocomplete_fields = ["prompt_image"]
	list_prefetch = ("answers__alternatives", "prompt_image")
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
		"prompt_text",
		"answers__alternatives__text",
	]

	def get_fieldsets(self, request, obj=None):
		return self.base_fieldsets(extra_fields=("min_correct_answers",))

	@admin.display(description="Prompt", ordering="prompt_text")
	def prompt_preview(self, instance):
		image_thumb_preview = get_admin_image_thumb_preview(
			instance.prompt_image.image if instance.prompt_image else None
		)

		if not instance.prompt_text and not image_thumb_preview:
			return None

		return format_html_join(
			"",
			'<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
			"  <span>{}</span>"
			"  <span>{}</span>"
			"</div>",
			((instance.prompt_text, image_thumb_preview),),
		)

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		answers = list(instance.answers.all())

		if not answers:
			return None

		# Reads the alternatives directly. The old version looked for a "text"
		# key that migration 0003 had already replaced, so every answer here
		# rendered as an empty bullet.
		answers_html = format_html_join(
			"",
			'<li style="margin:4px 0;">{}</li>',
			(
				(", ".join(alt.text for alt in answer.alternatives.all()),)
				for answer in answers
			),
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
			instance.min_correct_answers,
			answers_html,
		)


class MapPointerAnswerForm(AlternativesInlineForm):
	alternative_model = MapPointerAlternative

	# A real autocomplete against ``MapArea``, which is what replaced the
	# hand-written level picker: a schema enum rebuilt in JavaScript, its
	# load-order hack, and the view that dumped every area name into the page.
	# The widget is declared here rather than swapped in afterwards — a field
	# wires its choices into the widget it is constructed with, and one assigned
	# later renders against a bare list it cannot read.
	areas = forms.ModelMultipleChoiceField(
		queryset=MapArea.objects.all(),
		required=False,
		widget=AutocompleteSelectMultiple(
			MapPointerAnswerArea._meta.get_field("area"), admin.site
		),
		help_text=(
			"Every area this answer may be placed on — any one of them counts as "
			"correct. They must all be at the question's map level."
		),
	)

	class Meta(AlternativesInlineForm.Meta):
		model = MapPointerAnswer
		fields = ["order"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.instance.pk:
			self.fields["areas"].initial = MapArea.objects.filter(
				answer_links__answer=self.instance
			)

	def _save_alternatives(self, answer):
		super()._save_alternatives(answer)
		answer.area_links.all().delete()
		MapPointerAnswerArea.objects.bulk_create(
			[
				MapPointerAnswerArea(answer=answer, area=area, order=index)
				for index, area in enumerate(self.cleaned_data.get("areas") or [])
			]
		)


class MapPointerAnswerFormSet(MinCorrectAnswersFormSet):
	"""Repeats ``MapPointer._validate_content``'s level rule for admin saves.

	The model rule reads the areas linked to each answer, and those links are
	written from ``save_related`` — after ``save_model`` has already run it. On a
	create there is nothing linked yet either. Without this, an area from another
	level can be saved onto an answer the client could then never match, and the
	question fails to validate ever after on the link that was let in.

	The error goes on the field rather than the formset so the offending row is
	the one that lights up, and so the area can simply be removed and the
	question saved again.
	"""

	def clean(self):
		super().clean()
		if any(self.errors):
			return

		level = self.instance.level
		for form in self.forms:
			if not form.cleaned_data or form.cleaned_data.get("DELETE"):
				continue
			areas = list(form.cleaned_data.get("areas") or [])
			if not areas:
				form.add_error("areas", "Choose at least one area for this answer.")
				continue
			wrong_level = sorted({area.name for area in areas if area.level != level})
			if wrong_level:
				form.add_error(
					"areas",
					f"These areas are not level-{level} areas: "
					f"{', '.join(wrong_level)}.",
				)


class MapPointerAnswerInline(admin.TabularInline):
	model = MapPointerAnswer
	form = MapPointerAnswerForm
	formset = MapPointerAnswerFormSet
	extra = 0
	fields = ["order", "alternatives_text", "areas"]
	ordering = ["order", "id"]
	verbose_name = "Answer"
	verbose_name_plural = "Answers — each label and the areas it may be placed on"


@admin.register(MapPointer)
class MapPointerAdmin(AbstractQuizAdmin):
	inlines = [MapPointerAnswerInline]
	list_prefetch = ("answers__alternatives", "answers__area_links__area")
	list_display = [
		"id",
		"test_number",
		"question_number",
		"level",
		"is_active",
		"prompt_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	list_filter = ["level"] + without_category(AbstractQuizAdmin.list_filter)
	search_fields = AbstractQuizAdmin.search_fields + [
		"prompt_text",
		"answers__alternatives__text",
	]

	# Map questions are always geography ones, so the picker is left off and the
	# model default (GEOGRAPHY) stands.
	def get_fieldsets(self, request, obj=None):
		return self.base_fieldsets(
			extra_fields=("level", "show_answers", "min_correct_answers"),
			category=False,
		)

	@admin.display(description="Prompt", ordering="prompt_text")
	def prompt_preview(self, instance):
		return instance.prompt_text

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		answers = list(instance.answers.all())
		if not answers:
			return None

		return format_html_join(
			"",
			'<div style="margin:4px 0;"><strong>{}</strong> → <code>{}</code></div>',
			(
				(
					", ".join(alt.text for alt in answer.alternatives.all()),
					" / ".join(link.area.name for link in answer.area_links.all()),
				)
				for answer in answers
			),
		)
