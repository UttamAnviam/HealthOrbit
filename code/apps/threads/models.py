# threads_app/models.py

from django.db import models
import uuid
from django.utils.timezone import now

class Thread(models.Model):
    thread_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread_name= models.CharField(max_length=255,blank=True, null=True)
    doctor_name = models.CharField(max_length=255)
    doctor_id = models.CharField(max_length=255)
    content = models.TextField()
    uploaded_files = models.JSONField(default=list)  
    messages = models.JSONField(default=list)  
    created_date = models.DateTimeField(default=now, editable=False)
    

    def __str__(self):
        return f"Thread {self.thread_id} by {self.doctor_id}"

    def save(self, *args, **kwargs):
        # Additional processing can be done here before saving
        super().save(*args, **kwargs)
        
    
    

    