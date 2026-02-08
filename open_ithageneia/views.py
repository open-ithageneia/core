from inertia import render


def home(request):
    return render(request, "Index")

# TODO delete this -alkis
def map_example(request):
    return render(request, "MapExample")