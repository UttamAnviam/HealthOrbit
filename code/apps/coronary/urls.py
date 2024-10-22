from django.urls import path
from .views import FileUploadView

urlpatterns = [
    path('upload_and_query/', FileUploadView.as_view(), name='upload_and_query'),
]
