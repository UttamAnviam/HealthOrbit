import PyPDF2
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import UploadedFile
import pandas as pd
import csv
from typing import List, Dict
import json

# Data structure to hold user threads
user_threads: Dict[str, List[Dict[str, str]]] = {}

# Function to extract text from a PDF file
def extract_text_from_pdf(file: UploadedFile):
    pdf_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            pdf_text += page.extract_text() or ""
    except Exception as e:
        print(f"Error reading the PDF file: {e}")
    return pdf_text

# Function to extract text from a TXT file
def extract_text_from_txt(file: UploadedFile):
    try:
        content = file.read().decode("utf-8")
        return content
    except Exception as e:
        print(f"Error reading the TXT file: {e}")
        return ""

# Function to extract text from a CSV file
def extract_text_from_csv(file: UploadedFile):
    csv_text = ""
    try:
        content = file.read().decode("utf-8").splitlines()
        reader = csv.reader(content)
        for row in reader:
            csv_text += " ".join(row) + "\n"
    except Exception as e:
        print(f"Error reading the CSV file: {e}")
    return csv_text

# Function to extract text from an Excel file
def extract_text_from_excel(file: UploadedFile):
    try:
        excel_data = pd.read_excel(file)
        return excel_data.to_string(index=False)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return ""

# Function to split text into smaller chunks to fit token limits
def split_text_into_chunks(text, chunk_size=1500):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# Function to query Azure OpenAI API
def query_pdf_content(chunk_text, query):
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_OPENAI_API_KEY,
    }
    
    body = {
        "messages": [
            {
                "role": "user",
                "content": f"Analyze the following document: {chunk_text}. Based on this text, answer the question: {query}."
            }
        ]
    }

    try:
        response = requests.post(settings.AZURE_OPENAI_ENDPOINT, json=body, headers=headers)
        response_data = response.json()
        return response_data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error querying Azure OpenAI API: {e}")
        return f"Error querying Azure OpenAI API: {e}"

# Function to query Azure OpenAI API with chunks
def query_pdf_content_in_chunks(combined_text, query):
    chunks = split_text_into_chunks(combined_text)
    responses = []

    for chunk in chunks:
        response = query_pdf_content(chunk, query)
        responses.append(response)

    combined_response = "\n".join(responses)
    
    # Final query to Azure OpenAI to summarize combined responses
    final_response = query_pdf_content(combined_response,  """generate a final report.if asked to generate a coronere report , generate it in a detailed coronere  format with proper explanation 
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
performance.""")
    return final_response

# Endpoint to upload files and ask a question
@csrf_exempt
def upload_and_query(request):
    if request.method == "POST":
        files = request.FILES.getlist('files')
        query = request.POST.get('query')
        user_id = request.POST.get('user_id')

        combined_text = ""

        for file in files:
            filename = file.name.lower()

            # Handle PDF files
            if filename.endswith(".pdf"):
                pdf_text = extract_text_from_pdf(file)
                if not pdf_text:
                    print(f"No extractable text in PDF file: {file.name}")
                else:
                    combined_text += pdf_text + "\n"

            # Handle TXT files
            elif filename.endswith(".txt"):
                txt_text = extract_text_from_txt(file)
                combined_text += txt_text + "\n"

            # Handle CSV files
            elif filename.endswith(".csv"):
                csv_text = extract_text_from_csv(file)
                combined_text += csv_text + "\n"

            # Handle Excel files
            elif filename.endswith(".xls") or filename.endswith(".xlsx"):
                excel_text = extract_text_from_excel(file)
                combined_text += excel_text + "\n"

            else:
                print(f"Unsupported file type: {file.name}")
                return JsonResponse({"error": f"Unsupported file type: {file.name}"}, status=400)

        if not combined_text:
            print("No extractable text found in any file.")
            return JsonResponse({"error": "None of the provided files contain extractable text."}, status=400)

        print(f"Combined text extracted: {combined_text[:500]}")  # Log first 500 characters for debugging

        answer = query_pdf_content_in_chunks(combined_text, query)
        
        print(f"Azure OpenAI API response: {answer[:500]}")  # Log first 500 characters of the response for debugging
        
        return JsonResponse({"query": query, "answer": answer})

    return JsonResponse({"error": "Invalid request method"}, status=405)





# views.py
import requests
from django.http import JsonResponse
from django.views import View
from django.db import connections
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = "https://healthorbitaidev210772056557.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2023-03-15-preview"
AZURE_OPENAI_API_KEY = "949ef1d4da1a44759286a068bb4aef87"

# Schema information for the database
schema_info = """
You are an SQL expert. Please consider the following database schema for health management:

1. **Consultations Table**:
   - **Table Name**: `consultations`
   - **Columns**:
     - `id`: BIGINT UNSIGNED, not null
     - `patient_model_id`: BIGINT UNSIGNED, not null
     - `position`: INT, not null
     - `created_by_id`: BIGINT UNSIGNED, not null
     - `created_at`: TIMESTAMP, nullable
     - `updated_at`: TIMESTAMP, nullable

2. **Patients Files Table**:
   - **Table Name**: `patients_files`
   - **Columns**:
     - `id`: BIGINT UNSIGNED, not null
     - `session_model_id`: BIGINT UNSIGNED, nullable
     - `patient_id`: BIGINT UNSIGNED, nullable
     - `audio_file`: VARCHAR(255), nullable
     - `type_id`: INT, not null, default '0'
     - `state_id`: INT, not null, default '1'
     - `base_path`: VARCHAR(255), nullable
     - `disk`: VARCHAR(255), nullable
     - `path`: VARCHAR(255), nullable
     - `size`: BIGINT UNSIGNED, nullable
     - `uuid`: CHAR(36), nullable
     - `created_at`: TIMESTAMP, nullable
     - `updated_at`: TIMESTAMP, nullable

3. **Patient Personal Details Table**:
   - **Table Name**: `patient_personal_details`
   - **Columns**:
     - `id`: BIGINT UNSIGNED, not null
     - `uuid`: VARCHAR(255), nullable
     - `patient_id`: VARCHAR(255), not null
     - `name`: VARCHAR(255), not null
     - `age`: INT, nullable
     - `height`: INT, nullable
     - `weight`: INT, nullable
     - `avatar`: VARCHAR(255), nullable
     - `blood`: VARCHAR(255), nullable
     - `gender`: VARCHAR(255), not null
     - `date`: VARCHAR(255), nullable
     - `location`: VARCHAR(255), not null
     - `patient_type`: INT, nullable
     - `symptoms`: LONGTEXT, not null
     - `note`: LONGTEXT, nullable
     - `time_slot`: VARCHAR(255), nullable
     - `current_medication`: VARCHAR(255), nullable
     - `policy_enrolled`: VARCHAR(255), nullable
     - `doctor_id`: INT, nullable
     - `organisation_id`: BIGINT UNSIGNED, nullable
     - `assign_to`: INT, nullable
     - `created_by_id`: INT, nullable
     - `created_at`: TIMESTAMP, nullable
     - `updated_at`: TIMESTAMP, nullable
     - `deleted_at`: TIMESTAMP, nullable
     - `session_type`: INT, nullable

4. **Sessions Table**:
   - **Table Name**: `sessions`
   - **Columns**:
     - `id`: BIGINT UNSIGNED, not null
     - `consultation_model_id`: BIGINT UNSIGNED, not null
     - `symptoms`: LONGTEXT, nullable
     - `session_id`: VARCHAR(255), not null
     - `session_type`: VARCHAR(255), not null
     - `session_state`: INT, not null
     - `created_by_id`: BIGINT UNSIGNED, not null
     - `created_at`: TIMESTAMP, nullable
     - `updated_at`: TIMESTAMP, nullable

5. **Transcriptions Table**:
   - **Table Name**: `transcriptions`
   - **Columns**:
     - `id`: BIGINT UNSIGNED, not null
     - `created_by_id`: BIGINT UNSIGNED, not null
     - `session_model_id`: BIGINT UNSIGNED, nullable
     - `prompt_id`: BIGINT UNSIGNED, nullable
     - `language_code`: TEXT, nullable
     - `language_detect`: VARCHAR(255), nullable
     - `patient_file_id`: BIGINT UNSIGNED, nullable
     - `transcription`: LONGTEXT, nullable
     - `summary`: LONGTEXT, nullable
     - `translated_summary`: LONGTEXT, nullable
     - `mcd_codes`: TEXT, nullable
     - `citation_segments`: LONGTEXT, nullable
     - `translated_citations`: TEXT, nullable
     - `optimized_response_json`: LONGTEXT, nullable
     - `translated_transcript`: LONGTEXT, nullable
     - `optimized_transcript`: LONGTEXT, nullable
     - `translated_optimized_transcript`: LONGTEXT, nullable
     - `modify_transcript`: VARCHAR(255), nullable
     - `state_id`: INT, nullable
     - `type`: INT, nullable
     - `session_type`: INT, nullable
     - `exception`: LONGTEXT, nullable
     - `created_at`: TIMESTAMP, nullable
     - `updated_at`: TIMESTAMP, nullable
     - `note`: LONGTEXT, nullable
     - `conversation_type`: INT, nullable
"""


@method_decorator(csrf_exempt, name='dispatch')
class QueryView(View):
    def post(self, request):
        question = request.POST.get('question')
        doctor_id = request.POST.get('doctor_id')

        if not question or not doctor_id:
            return JsonResponse({'error': 'Both question and doctor_id are required.'}, status=400)

        # Generate the SQL query using Azure OpenAI
        prompt = f"{schema_info} {question}. Only return results where doctor_id = '{doctor_id}'."
        sql_query = self.query_azure_openai(prompt)

        # Log the SQL query for debugging
        print(f"Generated SQL Query: {sql_query}")  # Debugging output

        # Execute the SQL query
        with connections['mysql_db'].cursor() as cursor:
            try:
                cursor.execute(sql_query)
                result = cursor.fetchall()
            except Exception as e:
                return JsonResponse({'error': f'Database query execution failed: {str(e)}'}, status=500)

        if not result:
            return JsonResponse({'error': 'No results found.'}, status=404)

        # Format the result (custom formatting can be added)
        formatted_response = self.format_result(result, sql_query)

        return JsonResponse({'response': formatted_response})

    def query_azure_openai(self, prompt):
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY,
        }
        
        # Update the prompt to ensure only the SQL query is returned without any explanations or formatting
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful SQL assistant."},
                {"role": "user", "content": f"{prompt}\n\nProvide only the SQL query without any explanations or formatting, and do not include code block indicators."}
            ]
        }

        try:
            response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return str(e)

    def format_result(self, result, query):
        # You can implement your custom formatting here
        return [row[0] for row in result]  # Returning names as a list





@method_decorator(csrf_exempt, name='dispatch')
class ReferralSummaryView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)  # Parse JSON data from request body
            doctor_id = data.get('created_by_id')
            patient_id = data.get('session_model_id')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

        # Print the retrieved values for debugging
        print(doctor_id, '.-------', patient_id)

        if not doctor_id or not patient_id:
            return JsonResponse({'error': 'Both doctor_id and patient_id are required.'}, status=400)

        # Retrieve SOAP notes for the patient
        soap_notes = self.get_soap_notes(patient_id)
        if not soap_notes:
            return JsonResponse({'error': 'No SOAP notes found for the specified patient.'}, status=404)

        # Check if the retrieved SOAP notes are meaningful
        if not self.is_meaningful(soap_notes):
            return JsonResponse({'error': 'The provided notes do not contain meaningful information.'}, status=400)

        # Generate the referral letter using Azure OpenAI
        prompt = f"You are a professional medical assistant. Your task is to generate a formal referral letter to a general physician. The letter should be clear, concise, and include all necessary details for the physician to understand the patient's condition and needs.\n\ntranscription: {soap_notes}\n\nBased on the above transcription, please generate a professional referral letter, ensuring it includes:\n\nA clear explanation of the patient's condition, referencing relevant details from the transcription.\nA polite request for further evaluation, treatment, or investigation from the general physician.\nAny pertinent information regarding ongoing or past treatment.\n\nDon't include the heading and the sign-off."

        referral_summary = self.query_azure_openai(prompt)

        # Save the summary to the existing database table
        self.save_summary_to_db(doctor_id, patient_id, referral_summary)

        return JsonResponse({'summary': referral_summary})

    def is_meaningful(self, text):
        if len(text.split()) < 3 or all(word == 'you' for word in text.split()):
            return False
        return True

    def get_soap_notes(self, patient_id):
        print(patient_id, '----patient_id')
        with connections['mysql_db'].cursor() as cursor:
            cursor.execute("SELECT transcription FROM transcriptions WHERE session_model_id = %s", [patient_id])
            result = cursor.fetchone()
            print(result, '-------result')
        if result:
            return result[0]
        else:
            return None

    def save_summary_to_db(self, doctor_id, patient_id, summary):
        with connections['mysql_db'].cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO referral_summaries (created_by_id, session_model_id, summary) VALUES (%s, %s, %s)",
                    [doctor_id, patient_id, summary]
                )
                print([doctor_id, patient_id, summary], '-iiii')
            except Exception as e:
                return JsonResponse({'error': f'Database insertion failed: {str(e)}'}, status=500)

    def query_azure_openai(self, prompt):
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY,
        }
        
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful medical assistant."},
                {"role": "user", "content": prompt}
            ]
        }

        try:
            response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return str(e)





@method_decorator(csrf_exempt, name='dispatch')
class Discharge_Summary(View):
    def post(self, request):
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            doctor_id = data.get('created_by_id')
            patient_id = data.get('session_model_id')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

        # Print the retrieved values for debugging
        print("Doctor ID:", doctor_id, "Patient ID:", patient_id)

        if not doctor_id or not patient_id:
            return JsonResponse({'error': 'Both doctor_id and patient_id are required.'}, status=400)

        # Retrieve SOAP notes for the patient
        soap_notes = self.get_soap_notes(patient_id)
        if not soap_notes:
            return JsonResponse({'error': 'No SOAP notes found for the specified patient.'}, status=404)

        # Check if the retrieved SOAP notes are meaningful
        if not self.is_meaningful(soap_notes):
            return JsonResponse({'error': 'The provided SOAP notes do not contain meaningful information.'}, status=400)

        # Generate the discharge summary using Azure OpenAI
        prompt = (
            "Generate a detailed report for a patient's admission and discharge, including the following sections:\n\n"
            "1. Admission Details\n"
            "   - Chief Complaint: Provide a brief description of the presenting issue.\n"
            "   - Diagnosis: State the final diagnosis or impression.\n\n"
            "2. Treatment Provided\n"
            "   - Interventions: List the treatments and interventions provided in the Emergency Department (ED).\n"
            "   - Medications Administered: Detail any medications given, including dosages.\n\n"
            "3. Results of Investigations\n"
            "   - Pathology: Summarize key results from blood tests, urine tests, etc. (if applicable).\n"
            "   - Imaging: Include findings from X-rays, CT scans, MRIs, etc. (if applicable).\n\n"
            "4. Patient's Condition at Discharge\n"
            "   - General condition at the time of discharge.\n"
            "   - Vital Signs: Provide the latest recorded vital signs.\n\n"
            "5. Discharge Instructions\n"
            "   - Medications: List prescriptions given at discharge, with dosages and instructions.\n"
            "   - Activity Level: Recommend the level of activity (if applicable).\n"
            "   - Dietary Changes: Note any advised dietary changes or restrictions (if applicable).\n"
            "   - Wound Care: Include instructions for wound care, if applicable.\n"
            "   - Signs & Symptoms: Highlight any signs and symptoms to watch for that would necessitate a return to the hospital or further medical attention (if applicable).\n"
            "   - Follow-Up: Detail any scheduled follow-up appointments (if applicable)."
        )

        # Generate summary without saving to DB
        discharge_summary = self.query_azure_openai(prompt)

        # Return the summary in the response
        return JsonResponse({'summary': discharge_summary})

    def is_meaningful(self, text):
        # Basic check for meaningful content; enhance this with more sophisticated checks if needed
        if len(text.split()) < 3 or all(word == 'you' for word in text.split()):
            return False
        return True

    def get_soap_notes(self, patient_id):
        print("Fetching SOAP notes for Patient ID:", patient_id)
        with connections['mysql_db'].cursor() as cursor:
            cursor.execute("SELECT transcription FROM transcriptions WHERE session_model_id = %s", [patient_id])
            result = cursor.fetchone()
            print("SOAP notes result:", result)
        return result[0] if result else None

    def query_azure_openai(self, prompt):
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.AZURE_OPENAI_API_KEY,
        }
        
        data = {
            "model": "gpt-4o",  # Specify your model here
            "messages": [
                {"role": "system", "content": "You are a helpful medical assistant."},
                {"role": "user", "content": prompt}
            ]
        }

        try:
            response = requests.post(settings.AZURE_OPENAI_ENDPOINT, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            print("Error querying Azure OpenAI:", e)
            return JsonResponse({'error': f'Azure OpenAI request failed: {str(e)}'}, status=500)





from rest_framework.decorators import api_view

# Optional: Import Azure Speech SDK if you plan to use speech features
try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None


@api_view(['POST'])
def ai_assistant(request):
    prompt = request.data.get('prompt')
    use_speech = request.data.get('use_speech', False)

    if not prompt:
        return JsonResponse({"error": "Prompt is required"}, status=400)

    # Call Azure OpenAI to generate response
    azure_endpoint = "https://healthorbitaidev210772056557.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2023-03-15-preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": "949ef1d4da1a44759286a068bb4aef87",
    }

    data = {
        "messages": [{"role": "system", "content": "You are an assistant like Jarvis or Siri."},
                     {"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7,
        "top_p": 0.95,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }

    response = requests.post(azure_endpoint, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        assistant_response = result['choices'][0]['message']['content']

        # If speech is enabled, use text-to-speech to respond
        if use_speech and speechsdk:
            text_to_speech(assistant_response)
        
        return JsonResponse({"response": assistant_response})
    else:
        return JsonResponse({"error": "Failed to communicate with Azure OpenAI"}, status=response.status_code)


# Optional: Function to convert speech to text (if speech functionality is required)
def speech_to_text():
    if not speechsdk:
        return "Azure Speech SDK is not installed."
    
    speech_config = speechsdk.SpeechConfig(subscription="your-actual-speech-key-here", region="your-actual-region-here")
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

    print("Say something...")
    result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    else:
        return "Speech could not be recognized."


# Optional: Function to convert text to speech (if speech functionality is required)
def text_to_speech(text):
    if not speechsdk:
        return "Azure Speech SDK is not installed."
    
    speech_config = speechsdk.SpeechConfig(subscription="your-actual-speech-key-here", region="your-actual-region-here")
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    speech_synthesizer.speak_text_async(text)


