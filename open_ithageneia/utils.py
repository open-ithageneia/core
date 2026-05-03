from django.urls import Resolver404, resolve, reverse
from django.utils.html import format_html


def get_admin_image_thumb_preview(image):
	return (
		format_html('<img src="{}" style="height:50px" />', image.url) if image else ""
	)


def get_nav(request):
	items = {
		"home": ("Αρχική", "home"),
		"training": ("Τεστ προσομοίωσης", "quiz:training"),
		"dnd_playground": ("Drag N Drop playground", "quiz:dnd_playground"),
		"open_ended_playground": (
			"Open Ended playground",
			"quiz:open_ended_playground",
		),
		"multiple_choice_playground": (
			"Multiple Choice playground",
			"quiz:multiple_choice_playground",
		),
		"true_false_playground": (
			"True False playground",
			"quiz:true_false_playground",
		),
		"fill_in_the_blank_playground": (
			"Fill in the Blank playground",
			"quiz:fill_in_the_blank_playground",
		),
	}

	try:
		current_view = resolve(request.path_info).view_name
	except Resolver404:
		current_view = None

	nav_items = {}
	nav_list = []
	current_key = None

	for key, (label, view_name) in items.items():
		href = reverse(view_name)

		nav_items[key] = {"label": label, "href": href}
		nav_list.append({"key": key, "label": label, "href": href})

		if current_view == view_name:
			current_key = key

	return {
		"items": nav_items,
		"list": nav_list,
		"current": current_key,
	}
