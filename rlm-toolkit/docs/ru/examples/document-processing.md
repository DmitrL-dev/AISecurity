# Примеры обработки документов

Полные примеры для загрузки, анализа и извлечения данных из документов.

## Обработчик счетов

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float
    total: float

class Invoice(BaseModel):
    invoice_number: str
    date: date
    vendor_name: str
    vendor_address: Optional[str]
    subtotal: float
    tax: float
    total: float
    line_items: List[LineItem]

class InvoiceProcessor:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        
    def process(self, pdf_path: str) -> Invoice:
        docs = PDFLoader(pdf_path).load()
        text = "\n".join([doc.page_content for doc in docs])
        
        invoice = self.rlm.run_structured(
            f"Извлеки данные счёта из:\n\n{text}",
            output_schema=Invoice
        )
        return invoice
    
    def process_batch(self, pdf_paths: List[str]) -> List[Invoice]:
        return [self.process(path) for path in pdf_paths]

# Использование
processor = InvoiceProcessor()
invoice = processor.process("invoice_001.pdf")
print(f"Счёт #{invoice.invoice_number}")
print(f"Итого: {invoice.total:.2f}₽")
for item in invoice.line_items:
    print(f"  - {item.description}: {item.total:.2f}₽")
```

## Парсер резюме

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader, DOCXLoader
from pydantic import BaseModel
from typing import List, Optional

class Experience(BaseModel):
    company: str
    title: str
    duration: str
    description: Optional[str]

class Education(BaseModel):
    institution: str
    degree: str
    year: Optional[str]

class Resume(BaseModel):
    name: str
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    summary: Optional[str]
    skills: List[str]
    experience: List[Experience]
    education: List[Education]

class ResumeParser:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        
    def parse(self, file_path: str) -> Resume:
        if file_path.endswith(".pdf"):
            docs = PDFLoader(file_path).load()
        elif file_path.endswith(".docx"):
            docs = DOCXLoader(file_path).load()
        else:
            raise ValueError("Неподдерживаемый формат")
            
        text = docs[0].page_content
        
        return self.rlm.run_structured(
            f"Разбери это резюме:\n\n{text}",
            output_schema=Resume
        )
    
    def match_job(self, resume: Resume, job_description: str) -> float:
        result = self.rlm.run(f"""
        Оцени соответствие кандидата вакансии (0-100):
        
        Навыки кандидата: {', '.join(resume.skills)}
        Опыт: {len(resume.experience)} позиций
        
        Описание вакансии:
        {job_description}
        
        Верни только число.
        """)
        return float(result)

# Использование
parser = ResumeParser()
resume = parser.parse("ivan_petrov_resume.pdf")
print(f"Кандидат: {resume.name}")
print(f"Навыки: {', '.join(resume.skills)}")

job = "Ищем Python разработчика с опытом от 5 лет..."
score = parser.match_job(resume, job)
print(f"Соответствие: {score}%")
```

## Анализатор контрактов

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Clause(BaseModel):
    title: str
    summary: str
    risk_level: RiskLevel
    concerns: Optional[List[str]]

class ContractAnalysis(BaseModel):
    parties: List[str]
    effective_date: Optional[str]
    termination_date: Optional[str]
    total_value: Optional[str]
    key_clauses: List[Clause]
    overall_risk: RiskLevel
    recommendations: List[str]

class ContractAnalyzer:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        self.rlm.set_system_prompt("""
        Ты юрист-аналитик контрактов. Выявляй:
        - Ключевые стороны и даты
        - Финансовые условия
        - Рискованные области (ответственность, расторжение, штрафы)
        - Необычные или вызывающие беспокойство пункты
        Будь тщательным, но кратким.
        """)
        
    def analyze(self, pdf_path: str) -> ContractAnalysis:
        docs = PDFLoader(pdf_path).load()
        text = "\n".join([doc.page_content for doc in docs])
        
        return self.rlm.run_structured(
            f"Проанализируй этот контракт:\n\n{text[:50000]}",
            output_schema=ContractAnalysis
        )

# Использование
analyzer = ContractAnalyzer()
analysis = analyzer.analyze("service_agreement.pdf")
print(f"Стороны: {', '.join(analysis.parties)}")
print(f"Общий риск: {analysis.overall_risk}")
for clause in analysis.key_clauses:
    if clause.risk_level == RiskLevel.HIGH:
        print(f"⚠️ {clause.title}: {clause.summary}")
```

## Классификатор писем

```python
from rlm_toolkit import RLM
from pydantic import BaseModel
from typing import List
from enum import Enum

class EmailCategory(str, Enum):
    INQUIRY = "inquiry"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    SPAM = "spam"
    URGENT = "urgent"
    OTHER = "other"

class EmailAnalysis(BaseModel):
    category: EmailCategory
    sentiment: str  # positive, negative, neutral
    priority: int  # 1-5
    summary: str
    suggested_reply: str
    tags: List[str]

class EmailClassifier:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        
    def classify(self, subject: str, body: str) -> EmailAnalysis:
        return self.rlm.run_structured(
            f"""
            Проанализируй это письмо:
            
            Тема: {subject}
            Тело: {body}
            """,
            output_schema=EmailAnalysis
        )
    
    def auto_reply(self, analysis: EmailAnalysis) -> str:
        if analysis.category == EmailCategory.SPAM:
            return None
        return analysis.suggested_reply

# Использование
classifier = EmailClassifier()
result = classifier.classify(
    subject="Срочно: Заказ не получен",
    body="Я сделал заказ 10 дней назад и до сих пор не получил..."
)
print(f"Категория: {result.category}")
print(f"Приоритет: {result.priority}/5")
print(f"Предложенный ответ: {result.suggested_reply}")
```

## Генератор отчётов

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import DirectoryLoader, PDFLoader
from datetime import datetime

class ReportGenerator:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        
    def generate_summary_report(
        self, 
        source_dir: str, 
        report_type: str = "executive"
    ) -> str:
        loader = DirectoryLoader(
            path=source_dir, 
            glob="**/*.pdf", 
            loader_cls=PDFLoader
        )
        docs = loader.load()
        
        all_content = "\n\n---\n\n".join([
            f"Документ: {doc.metadata.get('source', 'Неизвестный')}\n{doc.page_content}"
            for doc in docs
        ])
        
        prompts = {
            "executive": "Создай executive summary (максимум 1 страница)",
            "detailed": "Создай детальный аналитический отчёт",
            "bullet": "Создай буллет-пойнт резюме ключевых находок"
        }
        
        report = self.rlm.run(f"""
        На основе этих документов:
        
        {all_content[:100000]}
        
        {prompts.get(report_type, prompts['executive'])}
        
        Включи:
        - Ключевые находки
        - Рекомендации
        - Следующие шаги
        
        Дата: {datetime.now().strftime('%Y-%m-%d')}
        """)
        
        return report
    
    def save_report(self, report: str, output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

# Использование
generator = ReportGenerator()
report = generator.generate_summary_report("./quarterly_data/", "executive")
generator.save_report(report, "Q3_Executive_Summary.md")
print(report)
```

## Суммаризатор медицинских записей

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from pydantic import BaseModel
from typing import List, Optional

class Medication(BaseModel):
    name: str
    dosage: str
    frequency: str

class Diagnosis(BaseModel):
    condition: str
    date: Optional[str]
    status: str  # active, resolved, chronic

class MedicalSummary(BaseModel):
    patient_name: str
    date_of_birth: Optional[str]
    blood_type: Optional[str]
    allergies: List[str]
    current_medications: List[Medication]
    diagnoses: List[Diagnosis]
    recent_visits: List[str]
    recommendations: List[str]

class MedicalRecordSummarizer:
    def __init__(self):
        self.rlm = RLM.from_openai("gpt-4o")
        self.rlm.set_system_prompt("""
        Ты аналитик медицинских записей. Извлекай информацию
        точно и полно. Отмечай любые тревожные паттерны.
        Соблюдай конфиденциальность пациента.
        """)
        
    def summarize(self, pdf_path: str) -> MedicalSummary:
        docs = PDFLoader(pdf_path).load()
        text = "\n".join([doc.page_content for doc in docs])
        
        return self.rlm.run_structured(
            f"Суммируй эту медицинскую запись:\n\n{text}",
            output_schema=MedicalSummary
        )

# Использование
summarizer = MedicalRecordSummarizer()
summary = summarizer.summarize("patient_records.pdf")
print(f"Пациент: {summary.patient_name}")
print(f"Активные состояния: {[d.condition for d in summary.diagnoses if d.status == 'active']}")
```

## Связанное

- [Галерея примеров](./index.md)
- [Туториал: RAG](../tutorials/03-rag.md)
- [How-to: Загрузчики](../how-to/loaders.md)
