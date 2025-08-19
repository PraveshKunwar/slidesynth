from google import genai
from dotenv import load_dotenv
import os
import time
from typing import List, Dict, Any
import re

class Summarizer:
    def __init__(self):
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini client: {str(e)}")
        
        self.TEMPERATURE = 0.7
        self.MAX_TOKENS = 300

    def generate_slides(self, structured_chunks: list, page_count: int = 0) -> list:
        slides = []
        
        if page_count > 0:
            target_slides = self._calculate_target_slides(page_count)
            max_chunks = min(len(structured_chunks), target_slides)
            print(f"\n📊 ADAPTIVE SLIDE COUNT:")
            print(f"  PDF Pages: {page_count}")
            print(f"  Target Slides: {target_slides}")
            print(f"  Available Chunks: {len(structured_chunks)}")
            print(f"  Processing Chunks: {max_chunks}")
        else:
            max_chunks = min(len(structured_chunks), 30)
            print(f"\n⚠️  No page count provided, using default limit: {max_chunks}")
        
        if len(structured_chunks) > max_chunks:
            print(f"\n⚠️  WARNING: Too many chunks ({len(structured_chunks)}). Limiting to first {max_chunks} chunks.")
            structured_chunks = structured_chunks[:max_chunks]
        
        print(f"\n=== PROCESSING {len(structured_chunks)} CHUNKS ===")
        
        for i, chunk in enumerate(structured_chunks):
            print(f"\nProcessing chunk {i+1}/{len(structured_chunks)}")
            try:
                prompt = self.create_prompt_for_chunk(chunk)
                raw_response = self.call_gemini_api(prompt)
                slide = self.parse_ai_response(raw_response)
                if self.validate_slide_quality(slide):
                    slides.append(slide)
                    print(f"✅ Slide {i+1} generated successfully")
                else:
                    fallback = self.generate_fallback_slide(chunk)
                    slides.append(fallback)
                    print(f"⚠️  Using fallback slide for chunk {i+1}")
            except Exception as e:
                fallback = self.generate_fallback_slide(chunk)
                slides.append(fallback)
                print(f"❌ Error processing chunk {i+1}: {str(e)}")
        
        print(f"\n=== FINAL RESULT ===")
        print(f"Total slides generated: {len(slides)}")
        print(f"Slide-to-page ratio: {len(slides)}/{page_count} = {len(slides)/page_count:.2f} slides per page")
        print("=" * 50)
        
        return slides
    
    def _calculate_target_slides(self, page_count: int) -> int:
        if page_count <= 0:
            return 10
        
        if page_count <= 10:
            return max(5, page_count // 2)
        elif page_count <= 30:
            return page_count // 3
        elif page_count <= 100:
            return page_count // 4
        else:
            return min(50, page_count // 5)
    def create_prompt_for_chunk(self, chunk_data: dict) -> str:
        """Creates a tailored prompt based on chunk content and metadata"""
        
        chunk_text = chunk_data.get('text', '')
        slide_type = chunk_data.get('slide_type', 'content')
        estimated_topic = chunk_data.get('estimated_topic', 'general')
        
        # Extract key themes and concepts from the text
        key_concepts = self._extract_key_concepts(chunk_text)
        
        # Create context-aware instructions
        slide_instructions = self._get_slide_type_instructions(slide_type)
        
        prompt = f"""You are an expert presentation designer. Create a professional slide from the following content.

CONTENT TO PROCESS:
{chunk_text}

SLIDE TYPE: {slide_type}
TOPIC AREA: {estimated_topic}
KEY CONCEPTS: {', '.join(key_concepts)}

INSTRUCTIONS:
{slide_instructions}

REQUIREMENTS:
1. Create a specific, descriptive title (NOT generic like "Summary" or "Overview")
2. Generate 3-5 clear, concise bullet points
3. Each bullet should be one complete idea (not fragments)
4. Focus on the most important information
5. Use active voice when possible
6. Ensure logical flow between bullets

OUTPUT FORMAT (JSON):
{{
    "title": "Specific descriptive title that captures the main concept",
    "bullets": [
        "First key point with specific details",
        "Second key point with specific details", 
        "Third key point with specific details"
    ]
}}

Generate the slide now:"""

        return prompt

    def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts and terms from the text"""
        # Remove common words and extract meaningful terms
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Filter for likely important concepts
        concepts = []
        for word in words:
            if (len(word) > 3 and 
                word not in ['The', 'This', 'That', 'They', 'There', 'These', 'Those'] and
                not re.match(r'^\d+$', word)):
                concepts.append(word)
        
        # Return top 5 most frequent unique concepts
        from collections import Counter
        concept_counts = Counter(concepts)
        return [concept for concept, _ in concept_counts.most_common(5)]

    def _get_slide_type_instructions(self, slide_type: str) -> str:
        """Get specific instructions based on slide type"""
        
        instructions = {
            'title': """
- Create an engaging title slide that introduces the main topic
- Include the primary subject and key themes
- Bullets should outline what will be covered or main objectives
- Focus on setting context and expectations""",
            
            'introduction': """
- Provide background context and setting
- Explain why this topic is important
- Include relevant historical context if applicable
- Set up the main narrative or argument""",
            
            'content': """
- Focus on the main ideas and supporting details
- Organize information hierarchically (most to least important)
- Include specific facts, data, or examples
- Ensure each bullet represents a distinct concept""",
            
            'methodology': """
- Explain approaches, methods, or processes
- Break down complex procedures into clear steps
- Include tools, techniques, or frameworks used
- Focus on "how" rather than "what" """,
            
            'results': """
- Present key findings, outcomes, or achievements
- Include specific data, statistics, or evidence
- Highlight the most significant results first
- Show cause-and-effect relationships where relevant""",
            
            'conclusion': """
- Summarize the main points or findings
- Draw connections between different concepts
- Include implications or significance
- End with key takeaways or next steps""",
            
            'data': """
- Present quantitative information clearly
- Include specific numbers, percentages, or statistics
- Explain what the data means or implies
- Compare different data points if relevant"""
        }
        
        return instructions.get(slide_type, instructions['content'])
    def call_gemini_api(self, prompt: str) -> str:
        MAX_RETRIES = 3
        RETRY_COUNT = 0
        
        while RETRY_COUNT < MAX_RETRIES:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    prompt=prompt,
                    temperature=self.TEMPERATURE,
                    max_output_tokens=self.MAX_TOKENS
                )
                
                response_text = response.text
                
                print(f"\n=== AI RESPONSE ===")
                print(f"Response Length: {len(response_text)} characters")
                print(f"Response Preview: {response_text[:300]}...")
                print("=" * 50)
                
                return response_text
                
            except Exception as e:
                if "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                    time.sleep(2 ** RETRY_COUNT)
                    RETRY_COUNT += 1
                else:
                    if RETRY_COUNT < MAX_RETRIES - 1:
                        RETRY_COUNT += 1
                        continue
                    else:
                        raise Exception(f"API call failed after retries: {str(e)}")
        
        raise Exception("Max retries exceeded")

    def parse_ai_response(self, raw_response: str) -> Dict[str, Any]:
        if not isinstance(raw_response, str):
            raise ValueError("raw_response must be a string")
            
        try:
            import json
            slide_data = json.loads(raw_response)
            
            if "title" in slide_data and "bullets" in slide_data:
                title = self._clean_text(slide_data["title"])
                bullets = [self._clean_text(bullet) for bullet in slide_data["bullets"]]
                
                return {
                    "title": title,
                    "bullets": bullets
                }
                
        except json.JSONDecodeError:
            title = self._extract_title_with_regex(raw_response)
            bullets = self._extract_bullets_with_regex(raw_response)
            
            if title and len(bullets) > 0:
                return {
                    "title": title,
                    "bullets": bullets
                }
        
        raise ValueError("Could not parse AI response into slide format")

    def validate_slide_quality(self, slide: Dict[str, Any]) -> bool:
        if not isinstance(slide, dict):
            return False
            
        title = slide.get("title", "")
        bullets = slide.get("bullets", [])
        
        if not isinstance(title, str) or not isinstance(bullets, list):
            return False
        
        # More lenient title validation
        if len(title) < 5 or len(title) > 150:
            return False
        
        # Only reject very generic titles
        overly_generic = ["title", "slide", "content", "text", "information"]
        if title.lower().strip() in overly_generic:
            return False
        
        # More lenient bullet validation
        if len(bullets) < 1 or len(bullets) > 8:
            return False
        
        valid_bullets = 0
        for bullet in bullets:
            if isinstance(bullet, str) and len(bullet.strip()) >= 10:
                valid_bullets += 1
        
        # At least 1 valid bullet is acceptable
        return valid_bullets >= 1

    def generate_fallback_slide(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        text = chunk_data.get("text", "")
        slide_type = chunk_data.get("slide_type", "content")
        estimated_topic = chunk_data.get("estimated_topic", "general")
        
        # Create more specific titles based on content analysis
        title = self._generate_contextual_title(text, slide_type, estimated_topic)
        
        # Extract meaningful bullet points from text
        bullets = self._extract_meaningful_bullets(text)
        
        if len(bullets) < 1:
            bullets = ["Key information from source material", "Please refer to original document for details"]
        
        return {
            "title": title,
            "bullets": bullets[:5]  # Limit to 5 bullets
        }

    def _generate_contextual_title(self, text: str, slide_type: str, topic: str) -> str:
        """Generate a meaningful title based on content analysis"""
        
        # Look for key phrases that could be titles
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return f"{topic.title()} Information"
        
        first_sentence = sentences[0]
        
        # Look for proper nouns and important concepts
        import re
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', first_sentence)
        
        if capitalized_words:
            # Use the most significant capitalized phrase
            longest_phrase = max(capitalized_words, key=len)
            
            if slide_type == "title":
                return f"{longest_phrase}: Overview"
            elif slide_type == "conclusion":
                return f"Key Outcomes: {longest_phrase}"
            elif slide_type == "introduction":
                return f"Understanding {longest_phrase}"
            else:
                return longest_phrase
        
        # Fallback to topic-based titles
        if slide_type == "title":
            return f"{topic.title()}: Introduction"
        elif slide_type == "conclusion":
            return f"{topic.title()}: Key Takeaways"
        elif slide_type == "methodology":
            return f"{topic.title()}: Approach and Methods"
        elif slide_type == "results":
            return f"{topic.title()}: Findings and Results"
        else:
            # Extract first meaningful phrase
            words = first_sentence.split()[:8]
            return ' '.join(words) if len(' '.join(words)) > 10 else f"{topic.title()} Overview"

    def _extract_meaningful_bullets(self, text: str) -> List[str]:
        """Extract meaningful bullet points from text"""
        sentences = [s.strip() for s in text.split('.') if s.strip() and len(s.strip()) > 15]
        
        bullets = []
        for sentence in sentences[:6]:  # Process up to 6 sentences
            # Clean up the sentence
            cleaned = sentence.strip()
            if len(cleaned) > 20 and len(cleaned.split()) >= 4:
                # Remove common prefixes
                cleaned = re.sub(r'^(The|This|That|These|Those|It|There)\s+', '', cleaned)
                bullets.append(cleaned)
        
        # If we don't have enough bullets, try splitting longer sentences
        if len(bullets) < 2 and sentences:
            for sentence in sentences[:3]:
                if len(sentence) > 100:  # Long sentence, try to split
                    parts = sentence.split(',')
                    for part in parts:
                        part = part.strip()
                        if len(part) > 20 and len(bullets) < 5:
                            bullets.append(part)
        
        return bullets

    def _clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        return text.strip().replace("\n", " ").replace("\t", " ")

    def _extract_title_with_regex(self, text: str) -> str:
        title_pattern = r'"title":\s*"([^"]+)"'
        match = re.search(title_pattern, text)
        if match:
            return self._clean_text(match.group(1))
        return ""

    def _extract_bullets_with_regex(self, text: str) -> List[str]:
        bullets_pattern = r'"bullets":\s*\[(.*?)\]'
        match = re.search(bullets_pattern, text, re.DOTALL)
        if match:
            bullets_text = match.group(1)
            bullet_items = re.findall(r'"([^"]+)"', bullets_text)
            return [self._clean_text(bullet) for bullet in bullet_items]
        return []