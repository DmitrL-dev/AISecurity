# Chatbot Examples

Complete chatbot implementations for various platforms and use cases.

## Customer Support Bot

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Load knowledge base (FAQ, policies, etc.)
docs = PDFLoader("support_docs.pdf").load()
vectorstore = ChromaVectorStore.from_documents(docs, OpenAIEmbeddings())

# Create support bot
class CustomerSupportBot:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        self.rlm.set_retriever(vectorstore.as_retriever(k=3))
        self.rlm.set_system_prompt("""
        You are a helpful customer support agent for TechCorp.
        - Be polite, professional, and empathetic
        - Answer based on the provided documentation
        - If you can't help, offer to transfer to a human agent
        - Keep responses concise and actionable
        """)
        
    def chat(self, user_message: str, session_id: str) -> str:
        return self.rlm.run(user_message)
    
    def transfer_to_human(self, reason: str) -> str:
        return f"Transferring to human agent. Reason: {reason}"

# Usage
bot = CustomerSupportBot()
print(bot.chat("How do I return a product?", "user123"))
print(bot.chat("I want to speak to a manager", "user123"))
```

## Multi-Language Bot

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory
from langdetect import detect

class MultiLanguageBot:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())
        
    def chat(self, message: str) -> str:
        try:
            lang = detect(message)
        except:
            lang = "en"
        
        self.rlm.set_system_prompt(f"""
        Respond in {lang} language.
        Be helpful, friendly, and concise.
        """)
        
        return self.rlm.run(message)

# Usage
bot = MultiLanguageBot()
print(bot.chat("Hello, how are you?"))         # English
print(bot.chat("Bonjour, comment ça va?"))     # French
print(bot.chat("Привет, как дела?"))           # Russian
print(bot.chat("こんにちは、元気ですか？"))     # Japanese
```

## Personality Bot

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory
from enum import Enum

class Personality(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    HUMOROUS = "humorous"
    ACADEMIC = "academic"

PERSONALITIES = {
    Personality.PROFESSIONAL: """
    You are a professional assistant. Be formal, precise, and business-focused.
    Use proper grammar and avoid colloquialisms.
    """,
    Personality.FRIENDLY: """
    You are a friendly companion. Be warm, casual, and supportive.
    Use emojis occasionally and show genuine interest.
    """,
    Personality.HUMOROUS: """
    You are a witty assistant. Include jokes, puns, and pop culture references.
    Keep things light but still be helpful.
    """,
    Personality.ACADEMIC: """
    You are a scholarly assistant. Be thorough, cite sources when possible,
    and explain concepts with precision and depth.
    """
}

class PersonalityBot:
    def __init__(self, personality: Personality = Personality.FRIENDLY):
        self.rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())
        self.set_personality(personality)
        
    def set_personality(self, personality: Personality):
        self.rlm.set_system_prompt(PERSONALITIES[personality])
        
    def chat(self, message: str) -> str:
        return self.rlm.run(message)

# Usage
bot = PersonalityBot(Personality.HUMOROUS)
print(bot.chat("Explain quantum physics"))
bot.set_personality(Personality.ACADEMIC)
print(bot.chat("Explain quantum physics"))
```

## Sales Bot

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from pydantic import BaseModel
from typing import Optional

class LeadInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    interest: Optional[str] = None
    budget: Optional[str] = None
    ready_to_buy: bool = False

class SalesBot:
    def __init__(self):
        self.memory = HierarchicalMemory()
        self.rlm = RLM.from_openai("gpt-4o", memory=self.memory)
        self.rlm.set_system_prompt("""
        You are a sales assistant for SaaS product "DataFlow".
        
        Goals:
        1. Qualify the lead (gather name, company, need, budget)
        2. Understand their pain points
        3. Present relevant features
        4. Overcome objections
        5. Guide toward a demo or trial
        
        Be persuasive but not pushy. Ask open-ended questions.
        """)
        self.lead_info = LeadInfo()
        
    def chat(self, message: str) -> str:
        response = self.rlm.run(message)
        self._extract_lead_info(message)
        return response
    
    def _extract_lead_info(self, message: str):
        # Extract info using structured output
        extraction_rlm = RLM.from_openai("gpt-4o-mini")
        info = extraction_rlm.run_structured(
            f"Extract lead info from: {message}",
            output_schema=LeadInfo,
            partial=True
        )
        # Merge with existing
        for field in LeadInfo.__fields__:
            if getattr(info, field):
                setattr(self.lead_info, field, getattr(info, field))
                
    def get_lead_info(self) -> LeadInfo:
        return self.lead_info

# Usage
bot = SalesBot()
print(bot.chat("Hi, I'm John from Acme Corp"))
print(bot.chat("We need help with data pipelines"))
print(bot.chat("Our budget is around $5000/month"))
print(f"Lead info: {bot.get_lead_info()}")
```

## Voice-Ready Bot (Whisper + TTS)

```python
import io
from openai import OpenAI
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

class VoiceBot:
    def __init__(self):
        self.client = OpenAI()
        self.rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())
        self.rlm.set_system_prompt("""
        You are a voice assistant. Keep responses:
        - Under 2-3 sentences
        - Easy to understand when spoken aloud
        - Conversational and natural
        """)
        
    def transcribe(self, audio_file: str) -> str:
        """Convert speech to text"""
        with open(audio_file, "rb") as f:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        return transcript.text
    
    def synthesize(self, text: str, output_file: str):
        """Convert text to speech"""
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        response.stream_to_file(output_file)
    
    def voice_chat(self, audio_input: str, audio_output: str) -> str:
        """Complete voice-to-voice interaction"""
        # Speech to text
        user_text = self.transcribe(audio_input)
        print(f"User said: {user_text}")
        
        # Generate response
        response_text = self.rlm.run(user_text)
        print(f"Bot says: {response_text}")
        
        # Text to speech
        self.synthesize(response_text, audio_output)
        
        return response_text

# Usage
bot = VoiceBot()
response = bot.voice_chat("input.mp3", "output.mp3")
```

## Contextual FAQ Bot

```python
from rlm_toolkit import RLM
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings
from typing import Dict, List

class FAQBot:
    def __init__(self, faqs: List[Dict[str, str]]):
        # Index FAQs
        self.embeddings = OpenAIEmbeddings()
        texts = [f"Q: {faq['question']}\nA: {faq['answer']}" for faq in faqs]
        self.vectorstore = ChromaVectorStore.from_texts(texts, self.embeddings)
        
        self.rlm = RLM.from_openai("gpt-4o")
        self.rlm.set_retriever(self.vectorstore.as_retriever(k=3))
        self.rlm.set_system_prompt("""
        You are an FAQ assistant. Answer based on the provided FAQ entries.
        If the question isn't covered, say so politely and offer to help otherwise.
        """)
        
    def ask(self, question: str) -> str:
        return self.rlm.run(question)
    
    def add_faq(self, question: str, answer: str):
        """Add new FAQ dynamically"""
        text = f"Q: {question}\nA: {answer}"
        self.vectorstore.add_texts([text])

# Usage
faqs = [
    {"question": "How do I reset my password?", "answer": "Click 'Forgot Password' on the login page..."},
    {"question": "What are your business hours?", "answer": "We're open Monday-Friday, 9am-6pm EST..."},
    {"question": "How do I cancel my subscription?", "answer": "Go to Settings > Subscription > Cancel..."}
]

bot = FAQBot(faqs)
print(bot.ask("I forgot my password"))
print(bot.ask("When are you open?"))
```

## Appointment Booking Bot

```python
from rlm_toolkit import RLM
from rlm_toolkit.tools import Tool
from datetime import datetime, timedelta
from typing import List

# Simulated calendar
available_slots = [
    datetime.now() + timedelta(days=1, hours=10),
    datetime.now() + timedelta(days=1, hours=14),
    datetime.now() + timedelta(days=2, hours=11),
]
booked_appointments = []

@Tool(name="get_available_slots", description="Get available appointment slots")
def get_available_slots() -> str:
    slots = [slot.strftime("%A %B %d at %I:%M %p") for slot in available_slots]
    return "Available slots:\n" + "\n".join(slots)

@Tool(name="book_appointment", description="Book an appointment")
def book_appointment(slot_description: str, name: str, email: str) -> str:
    # In reality, would parse slot_description and book
    booked_appointments.append({
        "slot": slot_description,
        "name": name,
        "email": email
    })
    return f"Appointment booked for {name} on {slot_description}. Confirmation sent to {email}."

from rlm_toolkit.agents import ReActAgent

class AppointmentBot:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[get_available_slots, book_appointment],
            system_prompt="""
            You are an appointment scheduling assistant.
            Help users find and book available appointment slots.
            Always confirm details before booking.
            """
        )
        
    def chat(self, message: str) -> str:
        return self.agent.run(message)

# Usage
bot = AppointmentBot()
print(bot.chat("I need to schedule an appointment"))
print(bot.chat("I'll take the first one. My name is John Smith, email john@example.com"))
```

## Related

- [Examples Gallery](./index.md)
- [Tutorial: Chatbots](../tutorials/02-chatbot.md)
