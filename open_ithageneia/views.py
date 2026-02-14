from inertia import render


def home(request):
    return render(request, "Index")

#  TODO made by alkis, remove
def language_test_example(request):
    return render(request, "LanguageTestExample")

