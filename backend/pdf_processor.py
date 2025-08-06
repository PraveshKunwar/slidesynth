from langchain_community.document_loaders import PyMuPDFLoader
import pprint
import os
import re

class Util:
    def is_meaningful_content(self, chunk: str) -> bool:
            clean = re.sub(r'[\w]', '', chunk)
            # skip if mostly numbers
            if sum(c.isdigit() for c in clean) / len(clean) > 0.7:
                return False
            # skip if to many single characters
            words = chunk.split()
            single_words = sum(1 for word in words if len(word.strip()) == 1)
            if len(words) > 0 and single_words / len(words) > 0.5:
                return False
            # skip if mostly references
            references = chunk.count('(') + chunk.count('[') + chunk.count(')')
            if references > len(chunk) * 0.1: # more than 10% reference characters
                return False
            # skip if contains common junk patterns
            junk_patterns = [
            r'^\d+$',  # Just page numbers
            r'^[A-Z\s]+$',  # All caps (likely headers without content)
            r'^\s*\.+\s*$',  # Just dots
            r'^\s*-+\s*$',  # Just dashes
            r'^Table \d+',  # Table headers without content
            r'^Figure \d+',  # Figure captions without content
            ]
            for pattern in junk_patterns:
                if re.match(pattern, chunk.strip()):
                    return False
            # must have at least 3 words for meaningful content
            meaningful_words = [word for word in words if len(words) > 2]
            if len(meaningful_words) < 3:
                return False
            return True
    def fix_artifacts(self):
        pass
    def normalize_academic_language(self):
        pass
    def remove_citations(self):
        pass
    def detect_topic_type(self):
        pass
    def determine_slide_type(self):
        pass
    def calculate_complexity_score(self):
        pass
    def generate_ai_context_hint(self):
        pass
class PDFProcessor:
# 1. Open the uploaded PDF file using a library like PyMuPDF

# 2. Loop through each page of the PDF

# 3. Extract the visible text from each page (ignore images or graphics for now)

# 4. Concatenate all page texts into one long string

# 5. Split the long string into logical chunks:
#    - Try to split by double newlines to get paragraphs
#    - Optionally detect headers or section titles
#    - Ignore any chunk that is too short or meaningless

# 6. Clean each chunk:
#    - Remove extra spaces, line breaks, and weird symbols
#    - Normalize characters and punctuation if needed

# 7. Package the cleaned chunks into a structured list or JSON format

# 8. Return these text chunks to the next step (e.g., AI summarizer)
    def __init__(self):
        self.util = Util()
    def extract_text_from_doc(self, path: str) -> str:
       # step 1
       loader = PyMuPDFLoader(path)
       docs = loader.load()
       # step 2 (seperate each page with double newlines)
       total_content = '\n\n'.join([doc.page_content for doc in docs])
       return total_content
           
    def chunk_text(self, text: str):
        # split paragraphs
        paragraphs = [paragraph for paragraph in text.split('\n\n')]
        # clean paragraphs
        for idx, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            paragraph = re.sub(r'[^\w\s\.,]', '', paragraph)
            if len(paragraph) >= 50:
                # possibly junk (look into optimal characters setting)
                paragraphs[idx] = paragraph
            else:
                continue
        # size management
        chunks = []
        for paragraph in paragraphs:
            if len(paragraph) >= 800:
                # too long for one slide, split further
                sentences = paragraph.split('.')
                curr_chunk = ""
                for sentence in sentences:
                    if len(curr_chunk) + len(sentence) < 800:
                        curr_chunk += sentence + '.'
                    else:
                        chunks.append(curr_chunk)
                        curr_chunk += sentence + '.'
                # add final curr_chunk
                chunks.append(curr_chunk)
            elif len(paragraph) >= 100:
                # good size
                chunks.append(paragraph)
            else:
                # too small, combine with last chunk
                if len(chunks) != 0 and len(chunks[-1]) < 600:
                    chunks[-1] += ' ' + paragraph
                else:
                # just add to chunks, don't combine
                    chunks.append(paragraph)
        # validate chunks, make sure it has genuine content
        final_chunks = []
        for chunk in chunks:
            if self.util.is_meaningful_content(chunk):
                final_chunks.append(chunk)
        return final_chunks
    def clean_and_structure_chunks(self, chunks):
        return "test"

a = PDFProcessor()
# Build absolute path to the PDF file
base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.normpath(
    os.path.join(base_dir, '..', 'public', 'documents', 'test_1.pdf')
)
if os.path.exists(file_path):
    b = a.extract_text_from_doc(file_path)
    c = a.chunk_text(b)
    print(c)
else:
    print(f"File not found: {file_path}")
    print(f"Current working directory: {os.getcwd()}")