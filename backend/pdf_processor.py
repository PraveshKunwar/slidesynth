from langchain_community.document_loaders import PyMuPDFLoader
import pprint
import os
import re
import nltk
from typing import List, Dict, Any

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class Util:
    def is_meaningful_content(self, chunk: str) -> bool:
        if not chunk or len(chunk.strip()) < 50:
            return False
            
        clean = re.sub(r'[^\w]', '', chunk)
        if len(clean) < 10:
            return False
            
        words = chunk.split()
        if len(words) < 5:
            return False
            
        single_words = sum(1 for word in words if len(word.strip()) == 1)
        if len(words) > 0 and single_words / len(words) > 0.3:
            return False
            
        references = chunk.count('(') + chunk.count('[') + chunk.count(')')
        if references > len(chunk) * 0.15:
            return False
            
        junk_patterns = [
            r'^\d+$',
            r'^[A-Z\s]+$',
            r'^\s*\.+\s*$',
            r'^\s*-+\s*$',
            r'^Table \d+',
            r'^Figure \d+',
            r'^Page \d+',
            r'^\d+$',
        ]
        
        for pattern in junk_patterns:
            if re.match(pattern, chunk.strip()):
                return False
                
        return True

    def fix_artifacts(self, text: str) -> str:
        text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
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
        text = re.sub(r'\([^)]*\d{4}[^)]*\)', '', text)
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\(see [^)]+\)', '', text)
        text = re.sub(r'\s+', ' ', text)
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
        
        technical_indicators = len(re.findall(r'\b\d+%\b', text))
        technical_indicators += len(re.findall(r'\bp\s*<\s*0\.\d+', text))
        technical_indicators += len(re.findall(r'\b[A-Z]{2,}\b', text))
        
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
    def __init__(self):
        self.util = Util()
        self.min_chunk_size = 200
        self.max_chunk_size = 800

    def extract_text_from_doc(self, path: str) -> str:
        loader = PyMuPDFLoader(path)
        docs = loader.load()
        total_content = '\n\n'.join([doc.page_content for doc in docs])
        return total_content

    def smart_split_paragraphs(self, text: str) -> List[str]:
        paragraphs = []
        
        lines = text.split('\n')
        current_paragraph = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                    current_paragraph = ""
                continue
            
            if self._is_likely_header(line):
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                current_paragraph = line
            else:
                if current_paragraph:
                    current_paragraph += " " + line
                else:
                    current_paragraph = line
        
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        return [p for p in paragraphs if self.util.is_meaningful_content(p)]

    def _is_likely_header(self, line: str) -> bool:
        if len(line) < 10:
            return False
        
        words = line.split()
        if len(words) > 8:
            return False
        
        if re.match(r'^\d+\.', line):
            return True
        
        if re.match(r'^[A-Z][A-Z\s]+$', line):
            return True
        
        if re.match(r'^[A-Z][a-z]+:', line):
            return True
        
        return False

    def split_into_sentences(self, text: str) -> List[str]:
        try:
            sentences = nltk.sent_tokenize(text)
            return [s.strip() for s in sentences if s.strip()]
        except:
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def create_balanced_chunks(self, sentences: List[str]) -> List[str]:
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.max_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks

    def chunk_text(self, text: str) -> List[str]:
        paragraphs = self.smart_split_paragraphs(text)
        all_chunks = []
        
        for paragraph in paragraphs:
            if len(paragraph) <= self.max_chunk_size:
                if len(paragraph) >= self.min_chunk_size:
                    all_chunks.append(paragraph)
                else:
                    if all_chunks and len(all_chunks[-1]) + len(paragraph) <= self.max_chunk_size:
                        all_chunks[-1] += " " + paragraph
                    else:
                        all_chunks.append(paragraph)
            else:
                sentences = self.split_into_sentences(paragraph)
                chunks = self.create_balanced_chunks(sentences)
                all_chunks.extend(chunks)
        
        final_chunks = []
        seen_chunks = set()
        
        for chunk in all_chunks:
            chunk_normalized = re.sub(r'\s+', ' ', chunk.strip()).lower()
            if chunk_normalized not in seen_chunks and self.util.is_meaningful_content(chunk):
                seen_chunks.add(chunk_normalized)
                final_chunks.append(chunk)
        
        return final_chunks

    def clean_and_structure_chunks(self, chunks: List[str]) -> List[Dict[str, Any]]:
        structured_chunks = []
        
        for idx, chunk in enumerate(chunks):
            cleaned = self.util.fix_artifacts(chunk)
            cleaned = self.util.normalize_academic_language(cleaned)
            cleaned = self.util.remove_citations(cleaned)
            
            if not self.util.is_meaningful_content(cleaned):
                continue
            
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

if __name__ == "__main__":
    processor = PDFProcessor()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.normpath(
        os.path.join(base_dir, '..', 'public', 'documents', 'test_3.pdf')
    )
    
    if os.path.exists(file_path):
        print(f"Processing: {file_path}")
        raw_text = processor.extract_text_from_doc(file_path)
        print(f"Raw text length: {len(raw_text)} characters")
        
        chunks = processor.chunk_text(raw_text)
        print(f"Generated {len(chunks)} chunks")
        
        structured_chunks = processor.clean_and_structure_chunks(chunks)
        print(f"Structured chunks: {len(structured_chunks)}")
        
        for i, chunk in enumerate(structured_chunks[:3]):
            print(f"\nChunk {i+1}:")
            print(f"  Type: {chunk['slide_type']}")
            print(f"  Length: {chunk['length']}")
            print(f"  Text: {chunk['text'][:100]}...")
    else:
        print(f"File not found: {file_path}")
        print(f"Current working directory: {os.getcwd()}")