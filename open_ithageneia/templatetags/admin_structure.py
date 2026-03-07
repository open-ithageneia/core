from django import template
from django.conf import settings

register = template.Library()


def pop_and_get_item(items_list, key, label):
	for index, item in enumerate(items_list):
		if item[key] == label:
			return items_list.pop(index)

	return None


@register.filter
def reorder_apps(auto_generated_apps):
	"""
	The logic is that we pop (get and remove) apps or models from the django auto generated lists
	and we put them in a new list called "reordered_%_popped_from_auto_generated_%" %(apps or app_models)
	and then we add these 2 list types in order to achieve custom ordering according to settings.ADMIN_STRUCTURE
	"""

	reordered_apps = []

	for item in settings.ADMIN_STRUCTURE:
		app_label = item[0]

		reordered_app = pop_and_get_item(auto_generated_apps, "app_label", app_label)

		if reordered_app:
			reordered_apps.append(reordered_app)
			reordered_app_models = []

			current_reordered_app_models = reordered_app.get("models")

			customly_reordered_app_ordered_models = item[1]

			for customly_ordered_model in customly_reordered_app_ordered_models:
				reordered_app_model = pop_and_get_item(
					current_reordered_app_models,
					"object_name",
					customly_ordered_model,
				)

				if reordered_app_model:
					reordered_app_models.append(reordered_app_model)

			reordered_app["models"] = (
				reordered_app_models + current_reordered_app_models
			)

	return reordered_apps + auto_generated_apps
