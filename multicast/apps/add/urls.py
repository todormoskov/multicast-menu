from django.urls import path

from . import views

app_name = "add"

urlpatterns = [
    path("", views.add_index, name="add_index"),
    path("file", views.add_stream_file, name="add_stream_file"),
    path("link", views.add_stream_link, name="add_stream_link"),
    path("manual", views.add_stream_manual, name="add_stream_manual"),
]