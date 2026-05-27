from django.urls import path
from . import views

app_name = "modules"

urlpatterns = [
    path("",         views.index,        name="index"),
    path("works/",   views.works_public, name="works"),
    path("contact/", views.contact,      name="contact"),
]
