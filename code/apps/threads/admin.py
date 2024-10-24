from django.contrib import admin

# Register your models here.
from apps.threads.models import Thread
admin.site.register(Thread)
