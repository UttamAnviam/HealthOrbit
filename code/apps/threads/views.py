import os
import PyPDF2
import requests  # Use requests to call Azure OpenAI
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import Thread
from .serializers import ThreadSerializer


import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

print(AZURE_OPENAI_ENDPOINT)


UPLOAD_DIR = "uploaded_files"

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer

    def create(self, request, *args, **kwargs):
        doctor_id = request.data.get('doctor_id')  # Changed to doctor_id
        doctor_name = request.data.get('doctor_name')
        content = request.data.get('content')
        uploaded_files = request.FILES.getlist('files')

        uploaded_file_names = []

        for uploaded_file in uploaded_files:
            file_location = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_location, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            uploaded_file_names.append(file_location)

        new_thread = Thread(
            doctor_name=doctor_name,
            doctor_id=doctor_id,
            content=content,
            uploaded_files=uploaded_file_names
        )
        new_thread.save()

        return Response({"message": "Thread created successfully!", "thread_id": str(new_thread.thread_id)}, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """Get All Threads"""
        threads = self.queryset
        serializer = self.get_serializer(threads, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Get a Thread by ID"""
        return super().retrieve(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete a Thread"""
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Thread deleted successfully!"}, status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """Update a Thread"""
        partial = request.data.get('partial', False)  # Allow partial updates
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def query_uploaded_files(self, request, *args, **kwargs):
        """Upload Files and Query the Document"""
        thread_id = kwargs.get('pk')
        query_text = request.data.get('query')

        try:
            thread = self.get_object()
        except Thread.DoesNotExist:
            return Response({"error": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)

        combined_text = ""
        uploaded_files = thread.uploaded_files

        for file_path in uploaded_files:
            if file_path.lower().endswith('.pdf'):
                combined_text += self.extract_text_from_pdf(file_path) + "\n"
            elif file_path.lower().endswith('.txt'):
                combined_text += self.extract_text_from_txt(file_path) + "\n"
            # Add other file types here (e.g., .csv, .xlsx) as needed

        response = self.query_pdf_content_in_chunks(combined_text, query_text)

        return Response({"query": query_text, "answer": response}, status=status.HTTP_200_OK)

    def continue_chat(self, request, *args, **kwargs):
        """Upload Files and Continue a Chat in an Existing Thread"""
        thread_id = kwargs.get('pk')
        query_text = request.data.get('query')

        try:
            thread = self.get_object()
        except Thread.DoesNotExist:
            return Response({"error": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)

        uploaded_files = request.FILES.getlist('files')
        combined_text = ""

        # Process the uploaded files and save them
        for uploaded_file in uploaded_files:
            file_location = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_location, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Append the new file to the existing uploaded_files
            thread.uploaded_files.append(file_location)

            # Optionally extract text from the new uploaded files
            if file_location.lower().endswith('.pdf'):
                combined_text += self.extract_text_from_pdf(file_location) + "\n"
            elif file_location.lower().endswith('.txt'):
                combined_text += self.extract_text_from_txt(file_location) + "\n"

        # Append the combined text to the existing content of the thread
        thread.content += "\n" + combined_text
        thread.save()

        response = self.query_pdf_content_in_chunks(thread.content, query_text)

        return Response({"query": query_text, "answer": response}, status=status.HTTP_200_OK)




    def extract_text_from_pdf(self, file_path):
        pdf_text = ""
        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() or ""
        except Exception as e:
            print(f"Error reading the PDF file: {e}")
        return pdf_text

    def extract_text_from_txt(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            print(f"Error reading the TXT file: {e}")
            return ""

    def query_pdf_content_in_chunks(self, combined_text, query):
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY  # Azure API key
        }
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Based on the following document: {combined_text}, answer this question: {query}."
                }
            ]
        }
        try:
            response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
            response.raise_for_status()  # Raise an error for bad responses
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error querying Azure OpenAI API: {e}")
            return f"Error querying Azure OpenAI API: {e}"
