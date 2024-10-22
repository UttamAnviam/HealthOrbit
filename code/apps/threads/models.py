# threads_app/models.py

from django.db import models
import uuid

class Thread(models.Model):
    thread_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor_name = models.CharField(max_length=255)
    doctor_id = models.CharField(max_length=255)
    content = models.TextField()
    uploaded_files = models.JSONField(default=list)  # Store file paths as a list
    messages = models.JSONField(default=list)  # Store messages as a list

    def __str__(self):
        return f"Thread {self.thread_id} by {self.doctor_id}"

    def save(self, *args, **kwargs):
        # Additional processing can be done here before saving
        super().save(*args, **kwargs)
        
    
    
# class Patient(models.Model):
    