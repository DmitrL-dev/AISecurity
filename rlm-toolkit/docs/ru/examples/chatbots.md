# Примеры чат-ботов

Полные реализации чат-ботов для различных платформ и сценариев.

## Бот поддержки клиентов

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Загрузка базы знаний (FAQ, политики и т.д.)
docs = PDFLoader("support_docs.pdf").load()
vectorstore = ChromaVectorStore.from_documents(docs, OpenAIEmbeddings())

class CustomerSupportBot:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        self.rlm.set_retriever(vectorstore.as_retriever(k=3))
        self.rlm.set_system_prompt("""
        Ты вежливый сотрудник поддержки компании TechCorp.
        - Будь вежливым, профессиональным и эмпатичным
        - Отвечай на основе предоставленной документации
        - Если не можешь помочь, предложи перевод на оператора
        - Держи ответы краткими и полезными
        """)
        
    def chat(self, user_message: str, session_id: str) -> str:
        return self.rlm.run(user_message)
    
    def transfer_to_human(self, reason: str) -> str:
        return f"Перевожу на оператора. Причина: {reason}"

# Использование
bot = CustomerSupportBot()
print(bot.chat("Как вернуть товар?", "user123"))
print(bot.chat("Хочу поговорить с менеджером", "user123"))
```

## Мультиязычный бот

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
        Отвечай на языке {lang}.
        Будь полезным, дружелюбным и кратким.
        """)
        
        return self.rlm.run(message)

# Использование
bot = MultiLanguageBot()
print(bot.chat("Hello, how are you?"))         # Английский
print(bot.chat("Bonjour, comment ça va?"))     # Французский
print(bot.chat("Привет, как дела?"))           # Русский
print(bot.chat("こんにちは、元気ですか？"))     # Японский
```

## Бот с персонажем

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
    Ты профессиональный ассистент. Будь формальным, точным и деловым.
    Используй правильную грамматику, избегай разговорных выражений.
    """,
    Personality.FRIENDLY: """
    Ты дружелюбный компаньон. Будь тёплым, неформальным и поддерживающим.
    Используй эмодзи иногда и показывай искренний интерес.
    """,
    Personality.HUMOROUS: """
    Ты остроумный ассистент. Включай шутки, каламбуры и отсылки к поп-культуре.
    Держи всё легко, но всё ещё будь полезным.
    """,
    Personality.ACADEMIC: """
    Ты учёный ассистент. Будь тщательным, цитируй источники по возможности,
    объясняй концепции точно и глубоко.
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

# Использование
bot = PersonalityBot(Personality.HUMOROUS)
print(bot.chat("Объясни квантовую физику"))
bot.set_personality(Personality.ACADEMIC)
print(bot.chat("Объясни квантовую физику"))
```

## Бот продаж

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
        Ты продавец-консультант SaaS продукта "DataFlow".
        
        Цели:
        1. Квалифицировать лида (собрать имя, компанию, потребность, бюджет)
        2. Понять их pain points
        3. Представить релевантные функции
        4. Преодолеть возражения
        5. Направить к демо или пробной версии
        
        Будь убедительным, но не навязчивым. Задавай открытые вопросы.
        """)
        self.lead_info = LeadInfo()
        
    def chat(self, message: str) -> str:
        response = self.rlm.run(message)
        self._extract_lead_info(message)
        return response
    
    def get_lead_info(self) -> LeadInfo:
        return self.lead_info

# Использование
bot = SalesBot()
print(bot.chat("Привет, я Иван из Яндекса"))
print(bot.chat("Нам нужна помощь с data pipelines"))
print(bot.chat("Наш бюджет около 300000₽ в месяц"))
print(f"Информация о лиде: {bot.get_lead_info()}")
```

## Голосовой бот (Whisper + TTS)

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
        Ты голосовой ассистент. Держи ответы:
        - До 2-3 предложений
        - Легко понимаемыми на слух
        - Разговорными и естественными
        """)
        
    def transcribe(self, audio_file: str) -> str:
        """Преобразование речи в текст"""
        with open(audio_file, "rb") as f:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        return transcript.text
    
    def synthesize(self, text: str, output_file: str):
        """Преобразование текста в речь"""
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        response.stream_to_file(output_file)
    
    def voice_chat(self, audio_input: str, audio_output: str) -> str:
        """Полное голосовое взаимодействие"""
        user_text = self.transcribe(audio_input)
        print(f"Пользователь сказал: {user_text}")
        
        response_text = self.rlm.run(user_text)
        print(f"Бот отвечает: {response_text}")
        
        self.synthesize(response_text, audio_output)
        
        return response_text

# Использование
bot = VoiceBot()
response = bot.voice_chat("input.mp3", "output.mp3")
```

## FAQ бот

```python
from rlm_toolkit import RLM
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings
from typing import Dict, List

class FAQBot:
    def __init__(self, faqs: List[Dict[str, str]]):
        self.embeddings = OpenAIEmbeddings()
        texts = [f"В: {faq['question']}\nО: {faq['answer']}" for faq in faqs]
        self.vectorstore = ChromaVectorStore.from_texts(texts, self.embeddings)
        
        self.rlm = RLM.from_openai("gpt-4o")
        self.rlm.set_retriever(self.vectorstore.as_retriever(k=3))
        self.rlm.set_system_prompt("""
        Ты FAQ ассистент. Отвечай на основе записей FAQ.
        Если вопрос не покрывается, вежливо скажи об этом.
        """)
        
    def ask(self, question: str) -> str:
        return self.rlm.run(question)
    
    def add_faq(self, question: str, answer: str):
        text = f"В: {question}\nО: {answer}"
        self.vectorstore.add_texts([text])

# Использование
faqs = [
    {"question": "Как сбросить пароль?", "answer": "Нажмите 'Забыли пароль' на странице входа..."},
    {"question": "Какой режим работы?", "answer": "Мы работаем Пн-Пт, 9:00-18:00 МСК..."},
    {"question": "Как отменить подписку?", "answer": "Настройки > Подписка > Отменить..."}
]

bot = FAQBot(faqs)
print(bot.ask("Забыл пароль"))
print(bot.ask("Когда вы работаете?"))
```

## Бот записи на приём

```python
from rlm_toolkit import RLM
from rlm_toolkit.tools import Tool
from rlm_toolkit.agents import ReActAgent
from datetime import datetime, timedelta

# Симуляция календаря
available_slots = [
    datetime.now() + timedelta(days=1, hours=10),
    datetime.now() + timedelta(days=1, hours=14),
    datetime.now() + timedelta(days=2, hours=11),
]
booked_appointments = []

@Tool(name="get_available_slots", description="Получить доступные слоты")
def get_available_slots() -> str:
    slots = [slot.strftime("%A %d %B в %H:%M") for slot in available_slots]
    return "Доступные слоты:\n" + "\n".join(slots)

@Tool(name="book_appointment", description="Забронировать приём")
def book_appointment(slot_description: str, name: str, email: str) -> str:
    booked_appointments.append({
        "slot": slot_description,
        "name": name,
        "email": email
    })
    return f"Приём забронирован для {name} на {slot_description}. Подтверждение отправлено на {email}."

class AppointmentBot:
    def __init__(self):
        self.agent = ReActAgent.from_openai(
            "gpt-4o",
            tools=[get_available_slots, book_appointment],
            system_prompt="""
            Ты ассистент по записи на приём.
            Помогай пользователям найти и забронировать слоты.
            Всегда подтверждай детали перед бронированием.
            """
        )
        
    def chat(self, message: str) -> str:
        return self.agent.run(message)

# Использование
bot = AppointmentBot()
print(bot.chat("Мне нужно записаться на приём"))
print(bot.chat("Возьму первый. Меня зовут Иван Петров, email ivan@example.com"))
```

## Связанное

- [Галерея примеров](./index.md)
- [Туториал: Чат-боты](../tutorials/02-chatbot.md)
