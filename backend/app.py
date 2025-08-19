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
from pptx_generator import PPTXGenerator

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health')
def health():
    return jsonify({"status": 200})

@app.route('/api/download-pptx/<filename>')
def download_pptx(filename):
    try:
        import tempfile
        temp_dir = tempfile.gettempdir()
        pptx_path = os.path.join(temp_dir, f"{filename}_slides.pptx")
        
        if os.path.exists(pptx_path):
            from flask import send_file
            return send_file(
                pptx_path,
                as_attachment=True,
                download_name=f"{filename}_slides.pptx",
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )
        else:
            return jsonify({'error': 'PPTX file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

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
            page_count = processor.get_page_count(save_path)
            chunks = processor.chunk_text(raw)
            structured_chunks = processor.clean_and_structure_chunks(chunks)
            
            print(f"\n=== CHUNK ANALYSIS ===")
            print(f"Raw text length: {len(raw)} characters")
            print(f"PDF pages: {page_count}")
            print(f"Initial chunks: {len(chunks)}")
            print(f"Structured chunks: {len(structured_chunks)}")
            
            if structured_chunks:
                print(f"\nFirst chunk sample:")
                first_chunk = structured_chunks[0]
                for key, value in first_chunk.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"  {key}: {value[:100]}...")
                    else:
                        print(f"  {key}: {value}")
            
            slides = summarizer.generate_slides(structured_chunks, page_count)
            
            print(f"\n=== PDF PROCESSING RESULTS ===")
            print(f"Filename: {filename}")
            print(f"PDF Pages: {page_count}")
            print(f"Total chunks: {len(structured_chunks)}")
            print(f"Total slides generated: {len(slides)}")
            print(f"Slide-to-page ratio: {len(slides)}/{page_count} = {len(slides)/page_count:.2f} slides per page")
            print(f"\n=== FIRST 3 SLIDES ===")
            for i, slide in enumerate(slides[:3]):
                print(f"Slide {i+1}:")
                print(f"  Title: {slide.get('title', 'N/A')}")
                print(f"  Bullets: {slide.get('bullets', [])}")
                print()
            
            if len(slides) > 3:
                print(f"... and {len(slides) - 3} more slides")
            print("=" * 50)
            
            pptx_generator = PPTXGenerator()
            pptx_path = pptx_generator.create_presentation(slides, filename.replace('.pdf', ''))
            
            print(f"\n=== PPTX GENERATION ===")
            print(f"PPTX file created: {pptx_path}")
            print("=" * 50)
            
        except Exception as e:
            os.remove(save_path)
            return jsonify({'error': f'Processing failed: {str(e)}'}), 500
        os.remove(save_path)
        return jsonify({
            'success': True,
            'filename': filename,
            'total_chunks': len(structured_chunks),
            'total_slides': len(slides),
            'slides': slides,
            'pptx_path': pptx_path
        })
    return jsonify({'error': 'Invalid file'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)