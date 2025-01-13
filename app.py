from flask import Flask, render_template, request, jsonify
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from msrest.authentication import CognitiveServicesCredentials
import os
import uuid
import time
from PIL import Image
import requests
import pandas as pd

app = Flask(__name__)

# Load the dataset
dataset_path = "dataset.csv"
dataset = pd.read_csv(dataset_path)

UPLOAD_FOLDER = './static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Azure API credentials
VISION_ENDPOINT = "https://ai-102-project.cognitiveservices.azure.com/"
VISION_KEY = "9CTd2qVrUkZkvTC9AB44vqrsSYFponfJm8Fi6KCZCxoZuuOK96KBJQQJ99BAACYeBjFXJ3w3AAAEACOGH83l"
TRANSLATION_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
TRANSLATION_KEY = "9CTd2qVrUkZkvTC9AB44vqrsSYFponfJm8Fi6KCZCxoZuuOK96KBJQQJ99BAACYeBjFXJ3w3AAAEACOGH83l"
TRANSLATION_REGION = "eastus"
SPEECH_API_KEY="9CTd2qVrUkZkvTC9AB44vqrsSYFponfJm8Fi6KCZCxoZuuOK96KBJQQJ99BAACYeBjFXJ3w3AAAEACOGH83l"
SPEECH_REGION="eastus"

# Initialize Azure clients
vision_client = ComputerVisionClient(VISION_ENDPOINT, CognitiveServicesCredentials(VISION_KEY))
speech_config = SpeechConfig(subscription=SPEECH_API_KEY, region=SPEECH_REGION)
translation_client = TextTranslationClient(endpoint=TRANSLATION_ENDPOINT, credential=AzureKeyCredential(TRANSLATION_KEY))

# Ensure uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        # Generate a unique filename and save the uploaded image
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}.jpg")
        file.save(file_path)

        # Get the URL of the uploaded image
        image_url = f"/static/uploads/{os.path.basename(file_path)}"

        # Detect text in image using Azure OCR
        title = extract_book_title(file_path)

        if not title:
            return jsonify({"error": "No text detected in image"}), 400

        # Match the title with the dataset
        description = match_title_with_dataset(title)
        if not description:
            description = "No matching title found in the dataset."

        # Return the image URL, title, and description to the frontend
        return jsonify({"image_url": image_url, "title": title, "description": description})

    return jsonify({"error": "No file uploaded"}), 400

def extract_book_title(image_path):
    """Extracts text from an image using Azure Computer Vision OCR."""
    with open(image_path, "rb") as image_stream:
        # Start asynchronous OCR operation
        ocr_results = vision_client.read_in_stream(image_stream, raw=True)
        operation_location = ocr_results.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]

        # Wait for the OCR result
        while True:
            result = vision_client.get_read_result(operation_id)
            if result.status not in ['notStarted', 'running']:
                break
            time.sleep(1)

        # Extract detected text
        if result.status == 'succeeded':
            for page_result in result.analyze_result.read_results:
                for line in page_result.lines:
                    print(line.text)
                    return line.text.strip()
    return None

def match_title_with_dataset(title):
    """Matches the extracted title with the dataset and returns the description."""
    title = title.lower()
    matches = dataset[dataset['title'].str.lower().str.contains(title)]
    if not matches.empty:
        return matches.iloc[0]['description']
    return None


@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    text = data.get('text')
    target_language = data.get('language')

    if text and target_language:
        try:
            headers = {
                'Ocp-Apim-Subscription-Key': TRANSLATION_KEY,
                'Ocp-Apim-Subscription-Region': TRANSLATION_REGION,
                'Content-Type': 'application/json'
            }
            body = [{"text": text}]
            translation_url = f"{TRANSLATION_ENDPOINT}/translate?api-version=3.0&to={target_language}"
            response = requests.post(translation_url, headers=headers, json=body)
            response.raise_for_status()
            translation_result = response.json()
            translated_text = translation_result[0]['translations'][0]['text']
            return jsonify({"translated_text": translated_text})
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Translation failed: {str(e)}"}), 10
    return jsonify({"error": "Invalid input"}), 10


@app.route('/narrate', methods=['POST'])
def narrate():
    data = request.json
    text = data.get('text')

    if text:
        speech_config.speech_synthesis_language = "en-US"
        synthesizer = SpeechSynthesizer(speech_config=speech_config)
        audio_stream = synthesizer.speak_text_async(text).get()

        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], "narration.mp3")
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_stream.audio_data)
        return jsonify({"audio_url": audio_path})
    return jsonify({"error": "No text provided"}),10

if __name__ == '__main__':
    app.run(debug=True)
