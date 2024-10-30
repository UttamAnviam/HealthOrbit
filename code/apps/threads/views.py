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

CORONER_REPORT_TEMPLATE = """generate a final report.if asked to generate a coroner's report , generate it in a detailed coroner  format with proper explanation 
                                       General principles
The report should be a detailed factual account, based on the
medical records and your knowledge of the deceased.
• Include your full name and qualifications (Bachelor of Medicine
rather than MB).
• Describe your status at the time you saw the patient (eg, GP
registrar or consultant surgeon for 10 years).
• Type your report on headed paper where possible using full,
grammatically correct sentences.
• Divide your report up into clear paragraphs. Numbering paragraphs
may make it easier to refer to sections of your report in case you're
asked to give evidence.
What to include
Be specific about your contact with the patient. For example, did
you see the patient on the NHS or privately?
Where appropriate, say if you saw the patient alone or with
someone else during each consultation. Give the name and status
of the other person (eg, spouse, mother, social worker).
Style
If you're ever
asked to write a
coroner's report,
it's important to
know what to
include.
21 July 2022
The report should stand on its own
Don't assume the reader has any knowledge of the case. Several
people may have to read the report apart from the coroner and they
may not have access to or be able to interpret the medical records.
Write in the first person
The reader should have a good idea of who did what, why, when, to
whom, and how you know this occurred. Be precise and explicit.
• Example: instead of writing, 'The patient was examined again later
in the day' - it's more helpful to say, 'I remember asking my
registrar, Dr Jane Smith, to examine the patient again later on the
same day, which, according to the notes, she did at [time].'
Concentrate on your observations and understanding
Provide a detailed account of your interaction with the patient
including the history you were given, what examination took place
and what your clinical findings were. Include any relevant negative
findings. Give an account of your differential diagnosis,
management plan and any safety netting advice that was given.
Avoid jargon or medical abbreviations
Your report will be read by those with no medical knowledge. All
medical terms are best written in full, avoiding abbreviations and
technical language, if possible. If you have to use abbreviations or medical terms, explain these. If you mention a drug, give an idea of
what type of drug it is and why it was prescribed. Give the full
generic name, dosage and route of administration.
• Example: many lay people might be familiar with abbreviating blood
pressure to 'BP'. But 'SOB' for 'shortness of breath' is less common,
and could be misinterpreted.
Clinical notes
Give a factual chronology of events as you saw them, referring
to the clinical notes whenever you can. Describe each and every
relevant consultation or phone contact in turn and include your
working diagnosis or your differential diagnoses.
Outline any hospital referrals, identifying the name of the relevant
practitioner or consultant.
The coroner will often require disclosure of the whole medical
record. You should also ensure you have had access to the full
medical record when preparing your report.
The absence of an entry may be important. Just as negative
findings are often important in clinical reports, with a coroner's
report it's important to think about what's not included, as well as
what is.
• Example: you're reporting on a case of a child who has died. The
pathologist finds healed fractures at post-mortem, but the notes
don't indicate that the parents sought medical advice for these
injuries. This raises the question of non-accidental injury and could
have serious and immediate implications for surviving children in the family.
Say what you found, but also what you looked for and failed to
find. If you failed to put yourself in a position to make an adequate
assessment, your evidence could be challenged. If your report
clearly demonstrates that your history and examination were
thorough, you are less likely to be called to explain your evidence at
an inquest.
Specify what the different details of your account are based
on. This could be your memory, the contemporaneous notes you or
others wrote, or your usual or normal practice. A coroner won't
expect you to make notes of every last detail, or to remember every
aspect of a consultation that at the time appeared to be routine. It's
perfectly acceptable to quote from memory, making it clear that this
is what you're doing or explaining what your normal practice would be under those circumstances.
Identify any other clinician involved in the care of the
deceased by their full name and professional status. Describe your
understanding of what they did and the conclusions they reached
based on your own knowledge or the clinical notes. You should not,
however, comment on the adequacy or otherwise of their
performance."""

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



