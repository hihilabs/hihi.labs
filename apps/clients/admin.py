from django.contrib import admin
from .models import Client, Contact, HostingSubscription
admin.site.register(Client)
admin.site.register(Contact)
admin.site.register(HostingSubscription)
