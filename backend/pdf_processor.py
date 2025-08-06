from langchain_community.document_loaders import PyMuPDFLoader
import pprint
import os
import re

class Util:
    def is_meaningful_content(self, chunk: str) -> bool:
            clean = re.sub(r'[^\w]', '', chunk)
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
            meaningful_words = [word for word in words if len(word) > 2]
            if len(meaningful_words) < 3:
                return False
            return True
    def fix_artifacts(self, text: str) -> str:
        text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)  # Fix hyphenated words split across lines
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between camelCase
        text = text.strip()
        return text
    def normalize_academic_language(self, text: str) -> str:
        replacements = {
        'aforementioned': 'previous',
        'thus': 'therefore',
        'hence': 'so',
        'whilst': 'while',
        'utilise': 'use',
        'demonstrate': 'show',
        'elucidate': 'explain',
        'commence': 'begin',
        'terminate': 'end'
        }
        for formal, casual in replacements.items():
            text = re.sub(rf'\b{formal}\b', casual, text, flags=re.IGNORECASE)
        return text
    def remove_citations(self, text: str) -> str:
        # Remove excessive citation patterns but keep some context
        text = re.sub(r'\([^)]*\d{4}[^)]*\)', '', text)  # Remove (Author, 2020) style citations
        text = re.sub(r'\[\d+\]', '', text)  # Remove [1] style citations
        text = re.sub(r'\(see [^)]+\)', '', text)  # Remove (see Appendix A) references
        text = re.sub(r'\s+', ' ', text)  # Clean up extra spaces left by removals
        return text.strip()
    def detect_topic_type(self, text: str) -> str:
        text_lower = text.lower()
        if any(word in text_lower for word in ['method', 'approach', 'procedure', 'design']):
            return 'methodology'
        elif any(word in text_lower for word in ['result', 'finding', 'data', 'table', 'figure']):
            return 'results'
        elif any(word in text_lower for word in ['conclusion', 'summary', 'implication', 'future']):
            return 'conclusion'
        elif any(word in text_lower for word in ['introduction', 'background', 'overview', 'problem']):
            return 'introduction'
        elif any(word in text_lower for word in ['literature', 'previous', 'prior', 'research']):
            return 'literature_review'
        else:
            return 'general'
    def determine_slide_type(self, text: str, position: int, total_chunks: int) -> str:
        if position == 0:
            return 'title'
        elif position < total_chunks * 0.3:
            return 'introduction'
        elif position > total_chunks * 0.8:
            return 'conclusion'
        else:
            text_lower = text.lower()
            if any(word in text_lower for word in ['table', 'figure', 'data', 'result']):
                return 'data'
            elif any(word in text_lower for word in ['method', 'procedure', 'approach']):
                return 'methodology'
            else:
                return 'content'
    def calculate_complexity_score(self, text: str) -> str:
        words = text.split()
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        # Count technical indicators
        technical_indicators = len(re.findall(r'\b\d+%\b', text))  # Percentages
        technical_indicators += len(re.findall(r'\bp\s*<\s*0\.\d+', text))  # P-values
        technical_indicators += len(re.findall(r'\b[A-Z]{2,}\b', text))  # Acronyms
        if avg_word_length > 6 or technical_indicators > 3:
            return 'high'
        elif avg_word_length > 4 or technical_indicators > 1:
            return 'medium'
        else:
            return 'low'
    def generate_ai_context_hint(self, slide_type: str, topic: str) -> str:
        context_map = {
        'title': 'Create a title slide with main topic and key themes',
        'introduction': 'Create an introduction slide with background context',
        'methodology': 'Create a methodology slide explaining approach and methods',
        'results': 'Create a results slide with key findings and data points',
        'data': 'Create a data presentation slide with clear statistics',
        'conclusion': 'Create a conclusion slide summarizing main points',
        'content': 'Create a content slide with main ideas and supporting points'
        }
        
        base_context = context_map.get(slide_type, 'Create a slide with main ideas')
        return f"{base_context}. Topic focus: {topic}"
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
           
    def chunk_text(self, text: str) -> list[str]:
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
    def clean_and_structure_chunks(self, chunks: list[str]) -> list[str]:
        structured_chunks = []
        for idx, chunk in enumerate(chunks):
            cleaned = self.util.fix_artifacts(chunk)
            cleaned = self.util.normalize_academic_language(cleaned)
            cleaned = self.util.remove_citations(cleaned)

            estimated_topic = self.util.detect_topic_type(cleaned)
            slide_type = self.util.determine_slide_type(cleaned, idx, len(chunks))
            complexity = self.util.calculate_complexity_score(cleaned)

            structured_chunk = {
                "text": cleaned,
                "estimated_topic": estimated_topic,
                "slide_type": slide_type,
                "length": len(cleaned),
                "complexity": complexity,
                "ai_context": self.util.generate_ai_context_hint(slide_type, estimated_topic)
            }
            structured_chunks.append(structured_chunk)
        return structured_chunks

a = PDFProcessor()
# Build absolute path to the PDF file
base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.normpath(
    os.path.join(base_dir, '..', 'public', 'documents', 'test_3.pdf')
)
if os.path.exists(file_path):
    b = a.extract_text_from_doc(file_path)
    c = a.chunk_text(b)
    d = a.clean_and_structure_chunks(c)
    pprint.pprint(d)
else:
    print(f"File not found: {file_path}")
    print(f"Current working directory: {os.getcwd()}")