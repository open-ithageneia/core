import logging

from django.contrib.messages import get_messages
from inertia import share

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

		share(request, messages=messages)

		response = self.get_response(request)

		return response
