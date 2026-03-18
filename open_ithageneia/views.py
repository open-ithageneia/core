from django.db import DatabaseError, connection
from django.http import JsonResponse
from inertia import render


def home(request):
	return render(request, "Index")


def healthcheck(request):
	try:
		with connection.cursor() as cursor:
			cursor.execute("SELECT 1")
		db_ok = True
	except DatabaseError:
		db_ok = False

	status = "ok" if db_ok else "degraded"
	http_status = 200 if db_ok else 503
	return JsonResponse({"status": status, "db": db_ok}, status=http_status)
