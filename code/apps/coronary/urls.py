from django.urls import path
from .views import FileUploadView

urlpatterns = [
    path('api/upload_and_query/', FileUploadView, name='upload_and_query'),
]
