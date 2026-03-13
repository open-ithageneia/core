import json

from quiz.models import FillInTheBlank, Statement, DragAndDrop, Matching
from import_export import resources, fields
from import_export.widgets import IntegerWidget, BooleanWidget


class StatementResource(resources.ModelResource):

	prompt_text = fields.Field(column_name="prompt_text")
	prompt_asset_id = fields.Field(column_name="prompt_asset_id", widget=IntegerWidget())

	choice1_text = fields.Field(column_name="choice1_text")
	choice1_asset_id = fields.Field(column_name="choice1_asset_id", widget=IntegerWidget())
	choice1_is_correct = fields.Field(column_name="choice1_is_correct", widget=BooleanWidget())

	choice2_text = fields.Field(column_name="choice2_text")
	choice2_asset_id = fields.Field(column_name="choice2_asset_id", widget=IntegerWidget())
	choice2_is_correct = fields.Field(column_name="choice2_is_correct", widget=BooleanWidget())

	choice3_text = fields.Field(column_name="choice3_text")
	choice3_asset_id = fields.Field(column_name="choice3_asset_id", widget=IntegerWidget())
	choice3_is_correct = fields.Field(column_name="choice3_is_correct", widget=BooleanWidget())

	choice4_text = fields.Field(column_name="choice4_text")
	choice4_asset_id = fields.Field(column_name="choice4_asset_id", widget=IntegerWidget())
	choice4_is_correct = fields.Field(column_name="choice4_is_correct", widget=BooleanWidget())

	class Meta:
		model = Statement
		fields = (
			"id",
			"type",
			"category",
		)

	def before_save_instance(self, instance, row, **kwargs):

		choices = []

		for i in range(1, 5):
			text = row.get(f"choice{i}_text")
			asset_id = row.get(f"choice{i}_asset_id")
			is_correct = row.get(f"choice{i}_is_correct")

			if text or asset_id:
				choices.append(
					{
						"text": text or "",
						"asset_id": asset_id,
						"is_correct": bool(is_correct),
					}
				)

		instance.content = {
			"prompt_text": row.get("prompt_text", ""),
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

