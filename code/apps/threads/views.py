import os
import PyPDF2
import requests
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import Thread
from .serializers import ThreadSerializer
from RagWithChat.pagination import CustomPagination
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

UPLOAD_DIR = "uploaded_files"

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

CORONER_REPORT_TEMPLATE = """Prepare a detailed and factual coroner's report directly in HTML format, structured with the following sections:

Author Details: Include the author’s full name, title (e.g., Bachelor of Medicine, rather than abbreviations), and role (e.g., Consultant Surgeon with [X] years of experience).

Case Information: Provide the patient’s details, including name, age, gender, consultation type (e.g., NHS), and any others present during consultations (e.g., spouse, social worker).

Clinical Chronology: Create a structured timeline detailing each consultation. Include dates, symptoms reported by the patient, examinations conducted, clinical findings, differential diagnoses, and any advice or referrals given.

Other Clinicians Involved: List any other clinicians, their roles, and summarize their contributions to the case without commenting on their performance.

Source of Information: Specify whether details are from contemporaneous clinical notes, direct observations, or standard practices.

Conclusion and Recommendations: Provide a summary of the case outcome and any further recommended investigations or actions.

Signature Section: Include a section with the author’s signature and date.

Structure the HTML using headers (<h1>, <h2>) for section titles and paragraphs (<p>) for content. Style it with inline CSS for readability, with clear section divisions and a clean layout. Ensure the report contains only the structured HTML content, with no additional explanations or comments."""

class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer
    pagination_class = CustomPagination
    
    def create(self, request, *args, **kwargs):
        doctor_id = request.data.get('doctor_id')
        doctor_name = request.data.get('doctor_name')
        content = request.data.get('content')
        thread_name = request.data.get('thread_name')
        uploaded_files = request.FILES.getlist('uploaded_files')  

        uploaded_file_names = []
        for uploaded_file in uploaded_files:
            file_location = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_location, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            uploaded_file_names.append(file_location)
        
        if ('coroner' in content.lower() or 'coronery' in content.lower()) and len(uploaded_file_names) == 0:
            return Response({"message": "Please upload the necessary documents for generating a coroner's report."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the content contains "coroner" or "coronery" and if more than one file is uploaded
        if len(uploaded_file_names) > 1 and ('coroner' in content.lower() or 'coronery' in content.lower()):
            content = CORONER_REPORT_TEMPLATE  # Use the coroner report template if conditions are met

        new_thread = Thread(
            doctor_name=doctor_name,
            thread_name=thread_name,
            doctor_id=doctor_id,
            content=content,
            uploaded_files=uploaded_file_names
        )
        new_thread.save()

        return Response({"message": "Thread created successfully!", "thread_id": str(new_thread.thread_id)}, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """Get All Threads or Filter by doctor_id"""
        doctor_id = request.query_params.get('doctor_id')  # Get doctor_id from query parameters
        if doctor_id:
            threads = Thread.objects.filter(doctor_id=doctor_id)  # Filter by doctor_id if present
        else:
            threads = Thread.objects.all()  # Return all threads if no doctor_id is provided
        page = self.paginate_queryset(threads)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
    
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

        # Query the Azure OpenAI API
        response = self.query_pdf_content_in_chunks(combined_text, query_text)

        # Save the question and answer to the thread's messages
        thread.messages.append({"question": query_text, "answer": response})
        thread.save()

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
        print(combined_text)
        thread.content += "\n" + combined_text

        # Query the Azure OpenAI API
        response = self.query_pdf_content_in_chunks(thread.content, query_text)

        # Save the question and answer to the thread's messages
        thread.messages.append({"question": query_text, "answer": response})
        thread.save()

        return Response({"query": query_text, "answer": response}, status=status.HTTP_200_OK)



    def text_question_answer(self, request, *args, **kwargs):
        """Add a Text-Based Question and Answer to an Existing Thread"""
        thread_id = kwargs.get('pk')
        question = request.data.get('question')
        answer = request.data.get('answer')

        try:
            thread = self.get_object()
        except Thread.DoesNotExist:
            return Response({"error": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)

        # Save the question and answer to the thread's messages
        thread.messages.append({"question": question, "answer": answer})
        thread.save()

        return Response({"message": "Question and answer added successfully!"}, status=status.HTTP_200_OK)



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
                    "content": f"Based on the following document: {combined_text}, answer this question: {query}. Give the response in HTML format"
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



