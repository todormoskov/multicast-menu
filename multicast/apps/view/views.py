from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse, JsonResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import DescriptionForm
from .models import Description, Stream


# Allow a user to create an account
def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("login"))
    else:
        form = UserCreationForm()

    return render(request, "registration/register.html", context={"form": form})


# Home page listing all active streams
def index(request):
    active_streams = list()
    for s in Stream.objects.filter(active=True).order_by("report_count"):
        descriptions = Description.objects.filter(stream=s)
        if descriptions.exists():
            active_streams.append((s, descriptions.order_by("-votes")[0].description))
        else:
            active_streams.append((s, "No title available"))
    
    return render(request, "view/index.html", context={"stream_list": active_streams})


# Detail page for a specific stream
def detail(request, stream_id):
    stream = get_object_or_404(Stream, id=stream_id)
    context = {
        "stream": stream,
        "descriptions": Description.objects.filter(stream=stream).order_by("-votes")[:3],
        "description_form": DescriptionForm() if request.user.is_authenticated else None,
    }

    return render(request, "view/play.html", context=context)


# Allow users to upvote a description
def upvote_description(request, description_id):
    description = get_object_or_404(Description, id=description_id)

    if request.is_ajax():
        description.upvote()
        return JsonResponse(dict())


# Allow users to downvote a description
def downvote_description(request, description_id):
    description = get_object_or_404(Description, id=description_id)

    if request.is_ajax():
        description.downvote()
        return JsonResponse(dict())


# Allow authenticated user to submit a stream description
@login_required
def submit_description(request, stream_id):
    stream = get_object_or_404(Stream, id=stream_id)

    if request.method == "POST":
        form = DescriptionForm(request.POST)
        if form.is_valid():
            description, created = Description.objects.get_or_create(
                user_submitted=request.user,
                stream=stream,
                description=form.cleaned_data["text"]
            )
            if not created:
                description.upvote()    
        return redirect(reverse("view:detail", kwargs={"stream_id": stream.id}))
    else:
        raise Http404


# Download a .m3u file for the user to open in VLC
def open(request, stream_id):
    stream = get_object_or_404(Stream, id=stream_id)

    response = HttpResponse()
    response["Content-Disposition"] = 'attachment; filename="playlist.m3u"'
    response.write("amt://{}@{}".format(stream.source, stream.group))
    if stream.udp_port:
        response.write(":{}".format(stream.udp_port))

    return response


# Allow users to report broken streams
def report_stream(request, stream_id):
    stream = get_object_or_404(Stream, id=stream_id)

    if request.is_ajax():
        stream.report()
        return JsonResponse(dict())
    else:
        raise Http404
