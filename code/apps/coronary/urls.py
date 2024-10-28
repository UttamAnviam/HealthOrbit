from django.urls import path
from .views import upload_and_query,QueryView,ReferralSummaryView,ai_assistant,Discharge_Summary

urlpatterns = [
    path('api/upload_and_query/', upload_and_query, name='upload_and_query'),
    path('api/query/', QueryView.as_view(), name='query'),  # Correct usage,
    path('api/referral-summary/', ReferralSummaryView.as_view(), name='referral_summary'),
    path('ai-assistant/', ai_assistant, name='ai_assistant'),
    path('api/discharge-summary/', Discharge_Summary.as_view(), name='discharge_summary')


]