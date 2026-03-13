from quiz.models import FillInTheBlank, Statement, DragAndDrop, Matching
import json
import re
from import_export import resources
from import_export import fields


class StatementResource(resources.ModelResource):
	prompt_text = fields.Field(column_name="prompt_text")
	prompt_asset_id = fields.Field(column_name="prompt_asset_id")

	class Meta:
		model = Statement
		fields = (
			"id",
			"type",
			"category",
		)

	choice_pattern = re.compile(r"choice(\d+)_text")

	def get_choice_numbers(self, row):
		"""Find all choice numbers present in the sheet."""
		numbers = []

		for key in row.keys():
			match = self.choice_pattern.match(key)
			if match:
				numbers.append(int(match.group(1)))

		return sorted(numbers)

	def build_choices(self, row):
		choices = []

		for i in self.get_choice_numbers(row):
			text = row.get(f"choice{i}_text")
			asset_id = row.get(f"choice{i}_asset_id")
			is_correct = row.get(f"choice{i}_is_correct")

			if not text and not asset_id:
				continue

			choice = {
				"text": text or "",
				"is_correct": bool(is_correct),
			}

			if asset_id:
				choice["asset_id"] = asset_id

			choices.append(choice)

		return choices

	def before_save_instance(self, instance, row, **kwargs):
		choices = self.build_choices(row)

		instance.content = {
			"prompt_text": row.get("prompt_text") or "",
			"prompt_asset_id": row.get("prompt_asset_id"),
			"choices": choices,
		}


class DragAndDropResource(resources.ModelResource):
	class Meta:
		model = DragAndDrop
		fields = ("id", "category")

	def before_save_instance(self, instance, row, **kwargs):
		left_values = [v.strip() for v in row["left_values"].split(",")]
		right_values = [v.strip() for v in row["right_values"].split(",")]

		instance.content = [
			{
				"title": row["left_title"],
				"values": left_values,
			},
			{
				"title": row["right_title"],
				"values": right_values,
			},
		]


class MatchingResource(resources.ModelResource):
	class Meta:
		model = Matching
		fields = ("id", "category")

	def before_save_instance(self, instance, row, **kwargs):
		left_items = [v.strip() for v in row["left_items"].split(",")]
		right_items = [v.strip() for v in row["right_items"].split(",")]

		left_objects = []
		right_objects = []

		for idx, text in enumerate(left_items, start=1):
			left_objects.append(
				{
					"id": idx,
					"text": text,
				}
			)

		for idx, text in enumerate(right_items, start=1):
			right_objects.append(
				{
					"id": idx,
					"text": text,
					"matched_id": idx,
				}
			)

		instance.content = [
			{
				"title": row["left_title"],
				"items": left_objects,
			},
			{
				"title": row["right_title"],
				"items": right_objects,
			},
		]


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
