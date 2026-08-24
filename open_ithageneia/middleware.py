import logging

from django.contrib.messages import get_messages
from inertia import share

from quiz.services import QuizService

from .utils import get_nav

logger = logging.getLogger(__name__)


class DataShareMiddleware(object):
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		messages = []
		for message in get_messages(request):
			message = {
				"message": message.message,
				"level": message.level,
				"tags": message.tags,
				"extra_tags": message.extra_tags,
				"level_tag": message.level_tag,
			}
			messages.append(message)

		if messages:
			logger.debug(
				"Sharing %d flash message(s) for %s", len(messages), request.path
			)

		user = getattr(request, "user", None)
		is_admin = bool(user and user.is_authenticated and user.is_staff)

		# Category names are shared rather than passed page by page: a question
		# card names the category of every quiz it renders, and it is nested too
		# deep in pages that don't otherwise care about categories to be handed
		# them as a prop.
		share(
			request,
			messages=messages,
			nav=get_nav(request),
			is_admin=is_admin,
			quiz_category_labels=QuizService.category_labels(),
		)

		response = self.get_response(request)

		return response
