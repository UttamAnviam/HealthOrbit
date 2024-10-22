import csv
import pandas as pd
import PyPDF2
import openai
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage

# Set your OpenAI API key
openai.api_key = "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"  # Replace with your actual OpenAI API key

class FileUploadView(View):
    @method_decorator(csrf_exempt)  # Exempt from CSRF for testing
    def post(self, request):
        files = request.FILES.getlist('files')
        query = request.POST.get('query')
        user_id = request.POST.get('user_id')

        combined_text = ""

        for file in files:
            filename = file.name.lower()
            if filename.endswith(".pdf"):
                pdf_text = self.extract_text_from_pdf(file)
                combined_text += pdf_text + "\n"
            elif filename.endswith(".txt"):
                txt_text = self.extract_text_from_txt(file)
                combined_text += txt_text + "\n"
            elif filename.endswith(".csv"):
                csv_text = self.extract_text_from_csv(file)
                combined_text += csv_text + "\n"
            elif filename.endswith(".xls") or filename.endswith(".xlsx"):
                excel_text = self.extract_text_from_excel(file)
                combined_text += excel_text + "\n"
            else:
                return JsonResponse({"error": f"Unsupported file type: {file.name}"}, status=400)

        if not combined_text:
            return JsonResponse({"error": "None of the provided files contain extractable text."}, status=400)

        answer = self.query_pdf_content_in_chunks(combined_text, query)
        
        return JsonResponse({"query": query, "answer": answer})

    def extract_text_from_pdf(self, file):
        pdf_text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() or ""
        except Exception as e:
            print(f"Error reading the PDF file: {e}")
        return pdf_text

    def extract_text_from_txt(self, file):
        try:
            content = file.read().decode("utf-8")
            return content
        except Exception as e:
            print(f"Error reading the TXT file: {e}")
            return ""

    def extract_text_from_csv(self, file):
        csv_text = ""
        try:
            content = file.read().decode("utf-8").splitlines()
            reader = csv.reader(content)
            for row in reader:
                csv_text += " ".join(row) + "\n"
        except Exception as e:
            print(f"Error reading the CSV file: {e}")
        return csv_text

    def extract_text_from_excel(self, file):
        try:
            excel_data = pd.read_excel(file)
            return excel_data.to_string(index=False)
        except Exception as e:
            print(f"Error reading the Excel file: {e}")
            return ""

    def split_text_into_chunks(self, text, chunk_size=1500):
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def query_pdf_content(self, chunk_text, query):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze the following document: {chunk_text}. Based on this text, answer the question: {query}."
                    }
                ]
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error querying OpenAI API: {e}")
            return f"Error querying OpenAI API: {e}"

    def query_pdf_content_in_chunks(self, combined_text, query):
        chunks = self.split_text_into_chunks(combined_text)
        responses = []

        for chunk in chunks:
            response = self.query_pdf_content(chunk, query)
            responses.append(response)

        combined_response = "\n".join(responses)

        # Final query to OpenAI API to summarize combined responses
        final_response = self.query_pdf_content(combined_response, "generate a final report based on the provided text.")
        return final_response
