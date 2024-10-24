from django.urls import path
from .views import upload_and_query,QueryView

urlpatterns = [
    path('api/upload_and_query/', upload_and_query, name='upload_and_query'),
    path('api/query/', QueryView.as_view(), name='query'),  # Correct usage

]