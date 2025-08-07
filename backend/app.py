from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTh'] = 50 * 1024 * 1024
CORS(app)
import os
from flask import request
from werkzeug.utils import secure_filename
from pdf_processor import PDFProcessor
from ai_summarizer import Summarizer

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    # Ensure a file part is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        # Process the PDF
        try:
            processor = PDFProcessor()
            summarizer = Summarizer()
            raw = processor.extract_text_from_doc(save_path)
            chunks = processor.chunk_text(raw)
            structured_chunks = processor.clean_and_structure_chunks(chunks)
            slides = summarizer.generate_slides(structured_chunks)
        except Exception as e:
            os.remove(save_path)
            return jsonify({'error': f'Processing failed: {str(e)}'}), 500
        os.remove(save_path)
        return jsonify({
            'success': True,
            'filename': filename,
            'total_chunks': len(structured_chunks),
            'total_slides': len(slides),
            'slides': slides
        })
    return jsonify({'error': 'Invalid file'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)