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
        
        # Historical content detection
        if any(word in text_lower for word in ['war', 'treaty', 'battle', 'military', 'dictator', 'hitler', 'stalin', 'fascism', 'nazism']):
            return 'historical_events'
        
        # Political content detection  
        elif any(word in text_lower for word in ['government', 'totalitarian', 'democracy', 'political', 'power', 'control']):
            return 'political_systems'
            
        # Geographic/territorial content
        elif any(word in text_lower for word in ['europe', 'asia', 'territory', 'country', 'nation', 'japan', 'germany']):
            return 'geography_politics'
            
        # Cause and effect content
        elif any(word in text_lower for word in ['cause', 'effect', 'result', 'consequence', 'impact', 'led to', 'resulted in']):
            return 'cause_and_effect'
            
        # Economic content
        elif any(word in text_lower for word in ['economic', 'reparations', 'payment', 'treaty of versailles', 'depression']):
            return 'economic_factors'
            
        # Biographical/people content
        elif any(word in text_lower for word in ['benito', 'mussolini', 'churchill', 'chamberlain', 'hideki tojo']):
            return 'historical_figures'
            
        # Methodological content
        elif any(word in text_lower for word in ['method', 'approach', 'procedure', 'design']):
            return 'methodology'
            
        # Results/data content
        elif any(word in text_lower for word in ['result', 'finding', 'data', 'table', 'figure', 'statistics']):
            return 'results'
            
        # Conclusion content
        elif any(word in text_lower for word in ['conclusion', 'summary', 'implication', 'future', 'takeaway']):
            return 'conclusion'
            
        # Introduction content  
        elif any(word in text_lower for word in ['introduction', 'background', 'overview', 'problem', 'context']):
            return 'introduction'
            
        else:
            return 'general_content'

    def determine_slide_type(self, text: str, position: int, total_chunks: int) -> str:
        text_lower = text.lower()
        
        # Check for specific content indicators first
        if any(phrase in text_lower for phrase in ['the big idea', 'key terms', 'main concept', 'overview']):
            return 'title'
        elif any(phrase in text_lower for phrase in ['reading check', 'summarize', 'analyze causes', 'what factors']):
            return 'analysis'
        elif any(phrase in text_lower for phrase in ['background', 'context', 'roots in', 'centuries-old']):
            return 'background'
        elif any(phrase in text_lower for phrase in ['militarists gain control', 'rise of', 'political control']):
            return 'historical_development'
        elif any(phrase in text_lower for phrase in ['treaty of versailles', 'failures of', 'dissatisfied']):
            return 'causes'
        elif any(phrase in text_lower for phrase in ['martha gellhorn', 'one american', 'personal account']):
            return 'personal_story'
        
        # Position-based typing as fallback
        elif position == 0:
            return 'title'
        elif position < total_chunks * 0.25:
            return 'introduction'
        elif position > total_chunks * 0.75:
            return 'conclusion'
        else:
            # Content-based typing for middle sections
            if any(word in text_lower for word in ['table', 'figure', 'data', 'result', 'statistics']):
                return 'data'
            elif any(word in text_lower for word in ['method', 'procedure', 'approach', 'how', 'process']):
                return 'methodology'
            elif any(word in text_lower for word in ['cause', 'reason', 'factor', 'led to', 'resulted in']):
                return 'causes'
            elif any(word in text_lower for word in ['effect', 'consequence', 'impact', 'outcome']):
                return 'effects'
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
            'title': 'Create an engaging title slide that introduces the main topic with clear objectives',
            'introduction': 'Create an introduction slide providing essential background and context',
            'background': 'Create a background slide explaining historical context and foundational information',
            'historical_development': 'Create a slide showing the progression and development of historical events',
            'causes': 'Create a slide explaining the causes, factors, and reasons that led to events',
            'effects': 'Create a slide detailing the consequences, impacts, and outcomes',
            'analysis': 'Create an analytical slide that examines and evaluates key aspects',
            'personal_story': 'Create a slide featuring personal accounts and human perspectives',
            'methodology': 'Create a methodology slide explaining approach and methods used',
            'results': 'Create a results slide with key findings and data points',
            'data': 'Create a data presentation slide with clear statistics and evidence',
            'conclusion': 'Create a conclusion slide summarizing main points and takeaways',
            'content': 'Create a content slide with main ideas and supporting details'
        }
        
        base_context = context_map.get(slide_type, 'Create a slide with main ideas and supporting points')
        
        # Add topic-specific guidance
        if 'historical' in topic.lower() or 'war' in topic.lower():
            topic_guidance = "Focus on historical events, key figures, dates, and cause-effect relationships"
        elif 'political' in topic.lower():
            topic_guidance = "Focus on political systems, government structures, and power dynamics"
        elif 'economic' in topic.lower():
            topic_guidance = "Focus on economic factors, financial impacts, and monetary consequences"
        else:
            topic_guidance = f"Focus on {topic} with specific details and examples"
            
        return f"{base_context}. {topic_guidance}."

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
    
    def get_page_count(self, path: str) -> int:
        import fitz
        try:
            doc = fitz.open(path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            print(f"Warning: Could not determine page count: {e}")
            return 0

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
        
        merged_chunks = self._merge_small_chunks(structured_chunks)
        print(f"\n=== CHUNK MERGING ===")
        print(f"Before merging: {len(structured_chunks)} chunks")
        print(f"After merging: {len(merged_chunks)} chunks")
        
        return merged_chunks
    
    def _merge_small_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(chunks) <= 1:
            return chunks
        
        merged = []
        current_chunk = chunks[0].copy()
        
        for next_chunk in chunks[1:]:
            combined_length = len(current_chunk["text"]) + len(next_chunk["text"])
            
            if combined_length <= self.max_chunk_size:
                current_chunk["text"] += " " + next_chunk["text"]
                current_chunk["length"] = len(current_chunk["text"])
                current_chunk["estimated_topic"] = self._merge_topics(
                    current_chunk["estimated_topic"], 
                    next_chunk["estimated_topic"]
                )
                current_chunk["slide_type"] = self._determine_merged_slide_type(
                    current_chunk["slide_type"], 
                    next_chunk["slide_type"]
                )
            else:
                merged.append(current_chunk)
                current_chunk = next_chunk.copy()
        
        merged.append(current_chunk)
        return merged
    
    def _merge_topics(self, topic1: str, topic2: str) -> str:
        if topic1 == topic2:
            return topic1
        elif topic1 == "general" and topic2 != "general":
            return topic2
        elif topic2 == "general" and topic1 != "general":
            return topic1
        else:
            return "general"
    
    def _determine_merged_slide_type(self, type1: str, type2: str) -> str:
        if type1 == type2:
            return type1
        elif type1 == "title" or type2 == "title":
            return "introduction"
        elif type1 == "conclusion" or type2 == "conclusion":
            return "content"
        else:
            return "content"

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