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

    def generate_slides(self, structured_chunks: list) -> list:
        slides = []
        max_chunks = 25
        
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
        print("=" * 50)
        
        return slides
    def create_prompt_for_chunk(self, chunk_data: dict) -> str:
        text = chunk_data["text"]
        slide_type = chunk_data["slide_type"] 
        topic = chunk_data["estimated_topic"]
        ai_context = chunk_data["ai_context"]

        base_prompt = "Convert this text into a presentation slide."
        if slide_type == "title":
            instructions = "Create a compelling title slide with main topic and key themes."
        elif slide_type == "methodology":
            instructions = "Focus on methods, approaches, and procedures. Make it clear and actionable."
        elif slide_type == "results":
            instructions = "Highlight key findings, data points, and important statistics."
        else:
            instructions = ai_context

        format_rules = """
        Return ONLY JSON format:
        {
        "title": "Clear, engaging slide title (5-10 words)",
        "bullets": ["Key point 1", "Key point 2", "Key point 3", "Key point 4"]
        }
        
        Requirements:
        - Title should be presentation-ready
        - 3-5 bullet points maximum
        - Each bullet should be concise but complete
        - Use simple, clear language
        """
        full_prompt = base_prompt + "\n" + instructions + "\n" + format_rules + "\n\nText: " + text
        
        print(f"\n=== AI PROMPT FOR CHUNK ===")
        print(f"Slide Type: {slide_type}")
        print(f"Topic: {topic}")
        print(f"Text Length: {len(text)} characters")
        print(f"Text Preview: {text[:200]}...")
        print("=" * 50)
        
        return full_prompt
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
        
        if len(title) < 3 or len(title) > 100:
            return False
        
        generic_words = ["introduction", "overview", "content", "summary", "conclusion"]
        if any(word in title.lower() for word in generic_words):
            return False
        
        if len(bullets) < 2 or len(bullets) > 6:
            return False
        
        for bullet in bullets:
            if not isinstance(bullet, str) or len(bullet) < 10:
                return False
            
            if sum(c.isdigit() or not c.isalnum() for c in bullet) > len(bullet) * 0.7:
                return False
        
        if len(set(bullets)) != len(bullets):
            return False
        
        return True

    def generate_fallback_slide(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        text = chunk_data.get("text", "")
        slide_type = chunk_data.get("slide_type", "content")
        topic = chunk_data.get("estimated_topic", "Topic")
        
        if slide_type == "title":
            title = f"Overview: {topic}"
        else:
            title = f"{topic.title()} Summary"
        
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        
        bullets = []
        for sentence in sentences:
            if len(bullets) < 4 and len(sentence) > 20:
                cleaned_sentence = self._clean_text(sentence)
                bullets.append(cleaned_sentence)
        
        if len(bullets) < 2:
            bullets.append("Key information from source material")
            bullets.append("Please refer to original document for details")
        
        return {
            "title": title,
            "bullets": bullets
        }

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