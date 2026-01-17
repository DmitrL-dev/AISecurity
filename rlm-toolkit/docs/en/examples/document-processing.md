# Document Processing Examples

Complete examples for document ingestion, analysis, and extraction.

## Invoice Processor

```python
from rlm_toolkit import RLM, RLMConfig
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
        # Load PDF
        docs = PDFLoader(pdf_path).load()
        text = "\n".join([doc.page_content for doc in docs])
        
        # Extract structured data
        invoice = self.rlm.run_structured(
            f"Extract invoice data from:\n\n{text}",
            output_schema=Invoice
        )
        return invoice
    
    def process_batch(self, pdf_paths: List[str]) -> List[Invoice]:
        return [self.process(path) for path in pdf_paths]

# Usage
processor = InvoiceProcessor()
invoice = processor.process("invoice_001.pdf")
print(f"Invoice #{invoice.invoice_number}")
print(f"Total: ${invoice.total:.2f}")
for item in invoice.line_items:
    print(f"  - {item.description}: ${item.total:.2f}")
```

## Resume Parser

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
        # Auto-detect format
        if file_path.endswith(".pdf"):
            docs = PDFLoader(file_path).load()
        elif file_path.endswith(".docx"):
            docs = DOCXLoader(file_path).load()
        else:
            raise ValueError("Unsupported format")
            
        text = docs[0].page_content
        
        return self.rlm.run_structured(
            f"Parse this resume:\n\n{text}",
            output_schema=Resume
        )
    
    def match_job(self, resume: Resume, job_description: str) -> float:
        """Return match score 0-100"""
        result = self.rlm.run(f"""
        Rate how well this candidate matches the job (0-100):
        
        Candidate skills: {', '.join(resume.skills)}
        Experience: {len(resume.experience)} positions
        
        Job Description:
        {job_description}
        
        Return only the number.
        """)
        return float(result)

# Usage
parser = ResumeParser()
resume = parser.parse("john_smith_resume.pdf")
print(f"Candidate: {resume.name}")
print(f"Skills: {', '.join(resume.skills)}")

job = "Looking for Python developer with 5+ years experience..."
score = parser.match_job(resume, job)
print(f"Match score: {score}%")
```

## Contract Analyzer

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
        You are a legal contract analyst. Identify:
        - Key parties and dates
        - Financial terms
        - Risk areas (liability, termination, penalties)
        - Unusual or concerning clauses
        Be thorough but concise.
        """)
        
    def analyze(self, pdf_path: str) -> ContractAnalysis:
        docs = PDFLoader(pdf_path).load()
        text = "\n".join([doc.page_content for doc in docs])
        
        return self.rlm.run_structured(
            f"Analyze this contract:\n\n{text[:50000]}",  # Limit for context
            output_schema=ContractAnalysis
        )
    
    def compare(self, contract1: str, contract2: str) -> str:
        """Compare two contracts and highlight differences"""
        docs1 = PDFLoader(contract1).load()
        docs2 = PDFLoader(contract2).load()
        
        return self.rlm.run(f"""
        Compare these two contracts and highlight key differences:
        
        CONTRACT 1:
        {docs1[0].page_content[:20000]}
        
        CONTRACT 2:
        {docs2[0].page_content[:20000]}
        
        Focus on: parties, terms, pricing, liability, termination
        """)

# Usage
analyzer = ContractAnalyzer()
analysis = analyzer.analyze("service_agreement.pdf")
print(f"Parties: {', '.join(analysis.parties)}")
print(f"Overall Risk: {analysis.overall_risk}")
for clause in analysis.key_clauses:
    if clause.risk_level == RiskLevel.HIGH:
        print(f"⚠️ {clause.title}: {clause.summary}")
```

## Medical Record Summarizer

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
        You are a medical records analyst. Extract key information
        accurately and completely. Flag any concerning patterns.
        Maintain patient privacy in outputs.
        """)
        
    def summarize(self, pdf_path: str) -> MedicalSummary:
        docs = PDFLoader(pdf_path).load()
        text = "\n".join([doc.page_content for doc in docs])
        
        return self.rlm.run_structured(
            f"Summarize this medical record:\n\n{text}",
            output_schema=MedicalSummary
        )
    
    def check_interactions(self, summary: MedicalSummary) -> str:
        """Check for potential drug interactions"""
        meds = [f"{m.name} {m.dosage}" for m in summary.current_medications]
        return self.rlm.run(f"""
        Check for potential drug interactions:
        Medications: {', '.join(meds)}
        Patient conditions: {', '.join([d.condition for d in summary.diagnoses])}
        Allergies: {', '.join(summary.allergies)}
        
        List any concerns.
        """)

# Usage
summarizer = MedicalRecordSummarizer()
summary = summarizer.summarize("patient_records.pdf")
print(f"Patient: {summary.patient_name}")
print(f"Active conditions: {[d.condition for d in summary.diagnoses if d.status == 'active']}")
print(summarizer.check_interactions(summary))
```

## Email Classifier

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
            Analyze this email:
            
            Subject: {subject}
            Body: {body}
            """,
            output_schema=EmailAnalysis
        )
    
    def batch_classify(self, emails: List[dict]) -> List[EmailAnalysis]:
        return [self.classify(e["subject"], e["body"]) for e in emails]
    
    def auto_reply(self, analysis: EmailAnalysis) -> str:
        if analysis.category == EmailCategory.SPAM:
            return None
        return analysis.suggested_reply

# Usage
classifier = EmailClassifier()
result = classifier.classify(
    subject="Urgent: Order not received",
    body="I placed an order 10 days ago and still haven't received it..."
)
print(f"Category: {result.category}")
print(f"Priority: {result.priority}/5")
print(f"Suggested reply: {result.suggested_reply}")
```

## Report Generator

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
        # Load all documents
        loader = DirectoryLoader(
            path=source_dir, 
            glob="**/*.pdf", 
            loader_cls=PDFLoader
        )
        docs = loader.load()
        
        # Combine content
        all_content = "\n\n---\n\n".join([
            f"Document: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}"
            for doc in docs
        ])
        
        # Generate report
        prompts = {
            "executive": "Create an executive summary (1 page max)",
            "detailed": "Create a detailed analysis report",
            "bullet": "Create a bullet-point summary of key findings"
        }
        
        report = self.rlm.run(f"""
        Based on these documents:
        
        {all_content[:100000]}
        
        {prompts.get(report_type, prompts['executive'])}
        
        Include:
        - Key findings
        - Recommendations
        - Next steps
        
        Date: {datetime.now().strftime('%Y-%m-%d')}
        """)
        
        return report
    
    def save_report(self, report: str, output_path: str):
        with open(output_path, "w") as f:
            f.write(report)

# Usage
generator = ReportGenerator()
report = generator.generate_summary_report("./quarterly_data/", "executive")
generator.save_report(report, "Q3_Executive_Summary.md")
print(report)
```

## Related

- [Examples Gallery](./index.md)
- [Tutorial: RAG](../tutorials/03-rag.md)
- [How-to: Loaders](../how-to/loaders.md)
