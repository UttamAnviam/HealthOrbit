from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ThreadViewSet

router = DefaultRouter()
router.register(r'threads', ThreadViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('threads/<uuid:pk>/query/', ThreadViewSet.as_view({'post': 'query_uploaded_files'}), name='query_uploaded_files'),
    path('threads/<uuid:pk>/continue-chat/', ThreadViewSet.as_view({'post': 'continue_chat'}), name='continue_chat'),
]
