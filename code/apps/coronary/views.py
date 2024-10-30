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
def query_pdf_content(chunk_text, query,temperature=0.01):
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
        ],
         "temperature": temperature
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
    final_response = query_pdf_content(combined_response,  """Prepare a detailed and factual coroner's report directly in HTML format, structured with the following sections:

Author Details: Include the author’s full name, title (e.g., Bachelor of Medicine, rather than abbreviations), and role (e.g., Consultant Surgeon with [X] years of experience).

Case Information: Provide the patient’s details, including name, age, gender, consultation type (e.g., NHS), and any others present during consultations (e.g., spouse, social worker).

Clinical Chronology: Create a structured timeline detailing each consultation. Include dates, symptoms reported by the patient, examinations conducted, clinical findings, differential diagnoses, and any advice or referrals given.

Other Clinicians Involved: List any other clinicians, their roles, and summarize their contributions to the case without commenting on their performance.

Source of Information: Specify whether details are from contemporaneous clinical notes, direct observations, or standard practices.

Conclusion and Recommendations: Provide a summary of the case outcome and any further recommended investigations or actions.

Signature Section: Include a section with the author’s signature and date.

Structure the HTML using headers (<h1>, <h2>) for section titles and paragraphs (<p>) for content. Style it with inline CSS for readability, with clear section divisions and a clean layout. Ensure the report contains only the structured HTML content, with no additional explanations or comments.""")
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
            created_by_id = data.get('created_by_id')
            patient_id = data.get('session_model_id')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

        # Print the retrieved values for debugging
        print(created_by_id, '.-------', patient_id)

        if not created_by_id:
            return JsonResponse({'error': 'created_by_id required.'}, status=400)
        
        if not patient_id: 
            return JsonResponse({'error': 'patient_id required.'}, status=400)

        # Retrieve SOAP notes for the patient
        soap_notes = self.get_soap_notes(patient_id)
        if not soap_notes:
            return JsonResponse({'error': 'No SOAP notes found for the specified patient.'}, status=404)

        # Check if the retrieved SOAP notes are meaningful
        if not self.is_meaningful(soap_notes):
            return JsonResponse({'error': 'The provided notes do not contain meaningful information.'}, status=400)

       # Generate the referral letter using Azure OpenAI
        prompt = (
            "You are a skilled medical assistant. Your task is to draft a professional referral letter to a general physician "
            "based on the transcription of SOAP notes provided. The letter should be formal, concise, and contain essential details "
            "for the physician to understand the patient’s current condition and clinical needs.\n\n"
            f"transcription: {soap_notes}\n\n"
            "Instructions for the referral letter:\n\n"
            "Patient's Condition: Provide a brief, clear summary of the patient's current condition, referencing key details from the transcription.\n"
            "Referral Purpose: Include a polite request for further evaluation, treatment, or necessary investigations to support the patient's care.\n"
            "Relevant Treatment History: Mention any pertinent ongoing or past treatments that the physician should consider.\n\n"
            "Please respond in an  HTML format with appropriate structure, including:\n\n"
            "- Clearly defined paragraphs.\n"
            "- Proper formatting for readability, with paragraph breaks where needed.\n"
            "Do not include a heading or sign-off."
            " For response create an object like below "
        )

        referral_summary = self.query_azure_openai(prompt)

        # Save the summary to the existing database table
        self.save_summary_to_db(created_by_id, patient_id, referral_summary)

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

    def save_summary_to_db(self, created_by_id, patient_id, summary):
        with connections['mysql_db'].cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO referral_summaries (created_by_id, session_model_id, summary) VALUES (%s, %s, %s)",
                    [created_by_id, patient_id, summary]
                )
                print([created_by_id, patient_id, summary], '-iiii')
            except Exception as e:
                return JsonResponse({'error': f'Database insertion failed: {str(e)}'}, status=500)

    def query_azure_openai(chunk_text, query, temperature=0.01):
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.AZURE_OPENAI_API_KEY,
        }
        
        body = {
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Analyze the following document: {chunk_text}. "
                        f"Based on this text, answer the question: {query}. "
                        "Please format your response in HTML."
                    )
                }
            ]
        }
        
        response = requests.post(
            settings.AZURE_OPENAI_ENDPOINT,
            headers=headers,
            json=body
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return {"error": f"Request failed with status code {response.status_code}"}





@method_decorator(csrf_exempt, name='dispatch')
class Discharge_Summary(View):
    def post(self, request):
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            created_by_id = data.get('created_by_id')
            session_model_id = data.get('session_model_id')
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

        # Print the retrieved values for debugging
        print("Doctor ID:", created_by_id, "Patient ID:", session_model_id)

        if not created_by_id :
            return JsonResponse({'error': 'created_by_id required.'}, status=400)

        if not session_model_id: 
            return JsonResponse({'error': 'session_model_id required.'}, status=400)
            
        # Retrieve SOAP notes for the patient
        soap_notes = self.get_soap_notes(session_model_id)
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
        "   - Follow-Up: Detail any scheduled follow-up appointments (if applicable).\n\n"
        
        "Generate this summary as an HTML template with clear formatting, including headings and bullet points as appropriate. Respond in the format: {html: \"<HTML content here>\"}."
    )


        # Generate summary without saving to DB
        discharge_summary = self.query_azure_openai(prompt)
        print(discharge_summary)
        # Return the summary in the response
        return JsonResponse({'summary': discharge_summary})

    def is_meaningful(self, text):
        # Basic check for meaningful content; enhance this with more sophisticated checks if needed
        if len(text.split()) < 3 or all(word == 'you' for word in text.split()):
            return False
        return True

    def get_soap_notes(self, session_model_id):
        print("Fetching SOAP notes for session_model_id ID:", session_model_id)
        with connections['mysql_db'].cursor() as cursor:
            cursor.execute("SELECT transcription FROM transcriptions WHERE session_model_id = %s", [session_model_id])
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
            "temperature": 0.01,
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


