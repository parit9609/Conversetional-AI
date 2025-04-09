import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, send_file, send_from_directory, flash
from google.cloud import texttospeech_v1
from google import genai
from google.genai import types

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
TTS_FOLDER = 'tts'
ALLOWED_EXTENSIONS = {'wav', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TTS_FOLDER'] = TTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TTS_FOLDER, exist_ok=True)
tts_client = texttospeech_v1.TextToSpeechClient()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files(folder):
    return sorted(os.listdir(folder), reverse=True)

def synthesize_speech(text, output_path):
    input_data = texttospeech_v1.SynthesisInput(text=text)
    voice = texttospeech_v1.VoiceSelectionParams(language_code="en-UK")
    audio_config = texttospeech_v1.AudioConfig(audio_encoding="LINEAR16")

    request = texttospeech_v1.SynthesizeSpeechRequest(
        input=input_data,
        voice=voice,
        audio_config=audio_config,
    )
    response = tts_client.synthesize_speech(request=request)

    with open(output_path, 'wb') as out:
        out.write(response.audio_content)

def generate_with_pdf_and_audio(audio_path, pdf_path, prompt_text):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    uploaded_audio = client.files.upload(file=audio_path)
    uploaded_pdf = client.files.upload(file=pdf_path)

    contents = [
        types.Content(role="user", parts=[
            types.Part.from_uri(file_uri=uploaded_audio.uri, mime_type=uploaded_audio.mime_type),
            types.Part.from_uri(file_uri=uploaded_pdf.uri, mime_type=uploaded_pdf.mime_type),
            types.Part.from_text(text=prompt_text),
        ])
    ]

    config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=config,
    )

    return response.text


@app.route('/')
def index():
    audio_files = get_files(app.config['UPLOAD_FOLDER'])
    tts_files = get_files(app.config['TTS_FOLDER'])
    return render_template('index.html', audio_files=audio_files, tts_files=tts_files)

@app.route('/ask_about_book', methods=['POST'])
def ask_about_book():
    pdf_file = request.files.get('pdf_file')
    audio_file = request.files.get('audio_data')

    if not (pdf_file and audio_file and allowed_file(pdf_file.filename) and allowed_file(audio_file.filename)):
        flash('Both PDF and Audio files are required.')
        return redirect('/')

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pdf_filename = f"{timestamp}.pdf"
    audio_filename = f"{timestamp}.wav"

    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
    tts_path = os.path.join(app.config['TTS_FOLDER'], f"{timestamp}_response.wav")
    txt_path = os.path.join(app.config['TTS_FOLDER'], f"{timestamp}_response.txt")
    

    pdf_file.save(pdf_path)
    audio_file.save(audio_path)

    
    prompt = "Briefly answer the user's question in the audio based on the content of the book."

    config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=1024,
        response_mime_type="text/plain",
    )

    gemini_response = generate_with_pdf_and_audio(audio_path, pdf_path, prompt)

    with open(txt_path, 'w') as f:
        f.write(gemini_response)
        
    synthesize_speech(gemini_response, tts_path)

    return redirect('/')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/tts/<filename>')
def get_tts_file(filename):
    return send_from_directory(app.config['TTS_FOLDER'], filename)

@app.route('/script.js', methods=['GET'])
def scripts_js():
    return send_file('./script.js')

if __name__ == '__main__':
    app.run(debug=True)
