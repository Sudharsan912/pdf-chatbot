from flask import Flask, render_template, request, jsonify
import PyPDF2
import os
from werkzeug.utils import secure_filename
import re
from collections import Counter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class PDFProcessor:
    def __init__(self):
        self.text = ""
        self.sentences = []

    def extract_text_from_pdf(self, pdf_file):
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            self.text = ""
            for page in pdf_reader.pages:
                self.text += page.extract_text()
            
            # Split into sentences (basic approach)
            self.sentences = [s.strip() for s in re.split('[.!?]', self.text) if s.strip()]
            return True
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return False

    def find_best_answer(self, question, num_sentences=2):
        if not self.sentences:
            return "Please upload a PDF first."

        # Convert question to lowercase for matching
        question = question.lower()
        
        # Remove question words for better matching
        question_words = set(['what', 'who', 'where', 'when', 'why', 'how'])
        question_terms = [w for w in question.split() if w not in question_words]

        # Score sentences based on matching terms
        scored_sentences = []
        for sentence in self.sentences:
            score = 0
            sentence_lower = sentence.lower()
            for term in question_terms:
                if term in sentence_lower:
                    score += 1
            if score > 0:
                scored_sentences.append((score, sentence))

        # Sort by score and return top sentences
        if scored_sentences:
            scored_sentences.sort(reverse=True)
            top_sentences = [sent for _, sent in scored_sentences[:num_sentences]]
            return " ".join(top_sentences)
        else:
            return "I couldn't find a relevant answer in the document."

pdf_processor = PDFProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        success = pdf_processor.extract_text_from_pdf(filepath)
        if success:
            return jsonify({'message': 'PDF processed successfully'})
        else:
            return jsonify({'error': 'Error processing PDF'})
    
    return jsonify({'error': 'Invalid file type'})

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'No question provided'})
    
    answer = pdf_processor.find_best_answer(question)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(debug=True)