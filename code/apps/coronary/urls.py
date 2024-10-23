from django.urls import path
from .views import upload_and_query

urlpatterns = [
    path('api/upload_and_query/', upload_and_query, name='upload_and_query'),
]
