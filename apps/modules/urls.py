from django.urls import path
from . import views

app_name = "modules"

urlpatterns = [
    path("",                              views.index,         name="index"),
    path("works/",                        views.works_public,  name="works"),
    path("contact/",                      views.contact,       name="contact"),
    path("sync/",                         views.sync_github,   name="sync_github"),
    path("seed/",                         views.seed_registry, name="seed_registry"),
    path("<int:pk>/toggle-public/",       views.toggle_public, name="toggle_public"),
    path("<int:pk>/update/",              views.update_field,  name="update_field"),
]
