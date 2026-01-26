# LLM09: Misinformation

> **Уровень:** ����������  
> **Время:** 35 минут  
> **Трек:** 02 — Threat Landscape  
> **Модуль:** 02.1 — OWASP LLM Top 10  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понять риски генерации misinformation LLM
- [ ] Изучить типы и причины hallucinations
- [ ] Освоить методы детектирования и митигации
- [ ] Интегрировать fact-checking в SENTINEL

---

## 1. Проблема Misinformation

### 1.1 Что такое Misinformation в LLM?

```
┌────────────────────────────────────────────────────────────────────┐
│                  LLM MISINFORMATION TYPES                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  HALLUCINATIONS:                                                   │
│  └── LLM "выдумывает" факты, которых нет                          │
│      • Fake citations                                              │
│      • Invented people/events                                      │
│      • Wrong but confident answers                                 │
│                                                                    │
│  FACTUAL ERRORS:                                                   │
│  └── Неверная информация из training data                         │
│      • Outdated facts                                              │
│      • Incorrect statistics                                        │
│      • Confused entities                                           │
│                                                                    │
│  MALICIOUS GENERATION:                                             │
│  └── Намеренное создание дезинформации                            │
│      • Propaganda                                                  │
│      • Fake news                                                   │
│      • Deepfakes (text)                                            │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Почему LLM Hallucinate?

| Причина | Описание | Пример |
|---------|----------|--------|
| **Statistical patterns** | LLM предсказывает "вероятные" слова | "The capital of Australia is Sydney" |
| **Knowledge cutoff** | Нет данных после даты обучения | Outdated CEO names |
| **Rare topics** | Мало training data | Obscure historical events |
| **Ambiguity** | Неоднозначный контекст | Wrong "John Smith" |
| **Overconfidence** | Уверенность без оснований | Invented citations |

---

## 2. Типы Hallucinations

### 2.1 Категории

```python
class HallucinationType:
    """Типы hallucinations"""
    
    CATEGORIES = {
        'factual': {
            'description': 'Неверные факты о реальном мире',
            'examples': [
                'Wrong dates/numbers',
                'Incorrect attributions',
                'False historical claims'
            ],
            'severity': 'high'
        },
        
        'intrinsic': {
            'description': 'Противоречие с предоставленным контекстом',
            'examples': [
                'Summarizing with wrong details',
                'Answering beyond the document',
                'Mixing up entities in text'
            ],
            'severity': 'high'
        },
        
        'extrinsic': {
            'description': 'Информация не в контексте и не verifiable',
            'examples': [
                'Adding plausible but unverified details',
                'Invented quotes',
                'Made-up sources'
            ],
            'severity': 'medium'
        },
        
        'coherence': {
            'description': 'Логически несовместимые утверждения',
            'examples': [
                'Self-contradicting statements',
                'Impossible scenarios',
                'Logical fallacies'
            ],
            'severity': 'medium'
        }
    }
```

### 2.2 Реальные Примеры

```python
# Задокументированные случаи hallucinations

real_world_examples = [
    {
        'case': 'Lawyer uses ChatGPT (2023)',
        'description': 'Адвокат использовал ChatGPT для research и подал иск со ссылками на 6 несуществующих судебных дел',
        'fake_cases': [
            'Varghese v. China Southern Airlines',
            'Shaboon v. Egyptair',
            # ... все выдуманные
        ],
        'consequence': 'Sanctions, public embarrassment',
        'lesson': 'Always verify AI-generated citations'
    },
    {
        'case': 'Google Bard launch (2023)',
        'description': 'На демо Bard заявил, что James Webb Telescope сделал первые фото экзопланеты, что неверно',
        'consequence': '$100B market cap loss for Alphabet',
        'lesson': 'Verify even simple factual claims'
    },
    {
        'case': 'Air Canada chatbot (2024)',
        'description': 'Chatbot дал неверную информацию о bereavement policy, компания была обязана выполнить',
        'consequence': 'Financial loss, legal liability',
        'lesson': 'AI responses can be legally binding'
    }
]
```

---

## 3. Детектирование Misinformation

### 3.1 Confidence Analysis

```python
class ConfidenceAnalyzer:
    """Анализ уверенности LLM"""
    
    def analyze_response(self, response: str, 
                         logprobs: list = None) -> dict:
        """Анализирует response на признаки неуверенности"""
        
        # Лингвистические маркеры неуверенности
        uncertainty_markers = [
            'I think', 'probably', 'maybe', 'might',
            'I believe', 'possibly', 'could be',
            'approximately', 'roughly', 'around'
        ]
        
        # Маркеры высокой уверенности (потенциально опасно)
        overconfidence_markers = [
            'definitely', 'certainly', 'absolutely',
            'without doubt', '100%', 'always', 'never'
        ]
        
        response_lower = response.lower()
        
        uncertainty_count = sum(
            1 for m in uncertainty_markers if m in response_lower
        )
        
        overconfidence_count = sum(
            1 for m in overconfidence_markers if m in response_lower
        )
        
        # Анализ logprobs если доступны
        token_confidence = None
        if logprobs:
            token_confidence = self._analyze_logprobs(logprobs)
        
        return {
            'uncertainty_markers': uncertainty_count,
            'overconfidence_markers': overconfidence_count,
            'token_confidence': token_confidence,
            'risk_assessment': self._assess_risk(
                uncertainty_count, overconfidence_count
            )
        }
    
    def _analyze_logprobs(self, logprobs: list) -> dict:
        """Анализирует logprobs для уверенности"""
        
        import math
        
        # Конвертируем logprobs в probabilities
        probs = [math.exp(lp) for lp in logprobs]
        
        avg_confidence = sum(probs) / len(probs)
        min_confidence = min(probs)
        
        # Ищем "uncertain" токены
        low_confidence_count = sum(1 for p in probs if p < 0.5)
        
        return {
            'average_confidence': avg_confidence,
            'min_confidence': min_confidence,
            'low_confidence_tokens': low_confidence_count,
            'total_tokens': len(probs)
        }
```

### 3.2 Fact Verification

```python
class FactVerifier:
    """Верификация фактов в LLM output"""
    
    def __init__(self, knowledge_base=None, search_api=None):
        self.kb = knowledge_base
        self.search = search_api
    
    def verify_claims(self, response: str) -> dict:
        """Извлекает и верифицирует claims"""
        
        # 1. Extract claims
        claims = self._extract_claims(response)
        
        # 2. Verify each claim
        results = []
        for claim in claims:
            verification = self._verify_claim(claim)
            results.append({
                'claim': claim,
                'verified': verification['verified'],
                'confidence': verification['confidence'],
                'sources': verification['sources']
            })
        
        # 3. Overall assessment
        verified_count = sum(1 for r in results if r['verified'])
        
        return {
            'total_claims': len(claims),
            'verified_claims': verified_count,
            'verification_rate': verified_count / len(claims) if claims else 1,
            'details': results
        }
    
    def _extract_claims(self, text: str) -> list:
        """Извлекает verifiable claims из текста"""
        
        # Используем NLP для извлечения утверждений
        claims = []
        
        # Ищем patterns с датами, числами, именами
        import re
        
        # Dates
        date_pattern = r'in \d{4}|on [A-Z][a-z]+ \d{1,2}'
        # Numbers
        number_pattern = r'\d+(?:\.\d+)?(?:\s*%|million|billion)?'
        # Named entities (simplified)
        entity_pattern = r'[A-Z][a-z]+ [A-Z][a-z]+'
        
        sentences = text.split('.')
        for sentence in sentences:
            if (re.search(date_pattern, sentence) or 
                re.search(number_pattern, sentence) or
                re.search(entity_pattern, sentence)):
                claims.append(sentence.strip())
        
        return claims
    
    def _verify_claim(self, claim: str) -> dict:
        """Верифицирует отдельный claim"""
        
        # 1. Check knowledge base
        if self.kb:
            kb_result = self.kb.query(claim)
            if kb_result['found']:
                return {
                    'verified': kb_result['matches'],
                    'confidence': kb_result['confidence'],
                    'sources': kb_result['sources']
                }
        
        # 2. Web search
        if self.search:
            search_results = self.search.query(claim)
            if search_results:
                return self._analyze_search_results(claim, search_results)
        
        return {
            'verified': None,
            'confidence': 0,
            'sources': []
        }
```

### 3.3 Citation Verification

```python
class CitationVerifier:
    """Верификация цитат и ссылок"""
    
    def verify_citations(self, response: str) -> dict:
        """Проверяет все citations в response"""
        
        # Extract citations
        citations = self._extract_citations(response)
        
        results = []
        for citation in citations:
            verification = self._verify_citation(citation)
            results.append({
                'citation': citation,
                **verification
            })
        
        fake_count = sum(1 for r in results if r['status'] == 'fake')
        
        return {
            'total_citations': len(citations),
            'verified': sum(1 for r in results if r['status'] == 'verified'),
            'fake': fake_count,
            'unknown': sum(1 for r in results if r['status'] == 'unknown'),
            'details': results,
            'warning': fake_count > 0
        }
    
    def _extract_citations(self, text: str) -> list:
        """Извлекает citations из текста"""
        
        import re
        
        citations = []
        
        # Academic style: (Author, Year)
        academic_pattern = r'\(([A-Z][a-z]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-z]+))?),?\s*(\d{4})\)'
        
        # URL style
        url_pattern = r'https?://[^\s]+'
        
        # Quote style
        quote_pattern = r'"([^"]+)"\s*[-–]\s*([A-Z][a-z]+ [A-Z][a-z]+)'
        
        for match in re.finditer(academic_pattern, text):
            citations.append({
                'type': 'academic',
                'author': match.group(1),
                'year': match.group(2),
                'raw': match.group(0)
            })
        
        for match in re.finditer(url_pattern, text):
            citations.append({
                'type': 'url',
                'url': match.group(0),
                'raw': match.group(0)
            })
        
        return citations
    
    def _verify_citation(self, citation: dict) -> dict:
        """Верифицирует отдельную citation"""
        
        if citation['type'] == 'url':
            return self._verify_url(citation['url'])
        
        elif citation['type'] == 'academic':
            return self._verify_academic(
                citation['author'],
                citation['year']
            )
        
        return {'status': 'unknown'}
    
    def _verify_url(self, url: str) -> dict:
        """Проверяет существование URL"""
        
        import requests
        
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                return {'status': 'verified', 'note': 'URL exists'}
            else:
                return {'status': 'fake', 'note': f'HTTP {response.status_code}'}
        except:
            return {'status': 'unknown', 'note': 'Could not verify'}
    
    def _verify_academic(self, author: str, year: str) -> dict:
        """Проверяет академическую citation через API"""
        
        # Использовать CrossRef, Semantic Scholar, etc.
        # Упрощённо:
        
        search_query = f"{author} {year}"
        
        # API call would go here
        # result = semantic_scholar.search(search_query)
        
        return {'status': 'unknown', 'note': 'Verification pending'}
```

---

## 4. Митигация

### 4.1 Prompt Engineering

```python
class MisinformationMitigation:
    """Методы снижения misinformation"""
    
    def create_grounded_prompt(self, query: str, 
                                context: str = None) -> str:
        """Создаёт prompt, снижающий hallucinations"""
        
        grounding_instructions = """
        IMPORTANT INSTRUCTIONS:
        
        1. Only provide information you are confident about
        2. If uncertain, say "I'm not sure" or "I don't have enough information"
        3. Distinguish between facts and opinions
        4. Do not invent citations or sources
        5. If asked about recent events, mention your knowledge cutoff
        6. Prefer "I don't know" over a potentially wrong answer
        """
        
        if context:
            # RAG-style: ground in provided context
            prompt = f"""
            {grounding_instructions}
            
            BASE YOUR ANSWER ON THIS CONTEXT ONLY:
            {context}
            
            If the context doesn't contain the answer, say so.
            
            QUESTION: {query}
            """
        else:
            prompt = f"""
            {grounding_instructions}
            
            QUESTION: {query}
            """
        
        return prompt
    
    def add_uncertainty_request(self, prompt: str) -> str:
        """Добавляет запрос на выражение uncertainty"""
        
        return prompt + """
        
        ADDITIONAL REQUIREMENT:
        For each factual claim you make, indicate your confidence level:
        - [HIGH CONFIDENCE]: Well-established facts
        - [MEDIUM CONFIDENCE]: Likely true but verify
        - [LOW CONFIDENCE]: Uncertain, may need verification
        """
```

### 4.2 Output Processing

```python
class OutputProcessor:
    """Обработка output для mitigation"""
    
    def __init__(self):
        self.confidence_analyzer = ConfidenceAnalyzer()
        self.fact_verifier = FactVerifier()
        self.citation_verifier = CitationVerifier()
    
    def process_response(self, response: str) -> dict:
        """Полная обработка response"""
        
        # 1. Analyze confidence
        confidence = self.confidence_analyzer.analyze_response(response)
        
        # 2. Verify facts
        facts = self.fact_verifier.verify_claims(response)
        
        # 3. Verify citations
        citations = self.citation_verifier.verify_citations(response)
        
        # 4. Generate warnings
        warnings = self._generate_warnings(confidence, facts, citations)
        
        # 5. Create annotated response
        annotated = self._annotate_response(response, facts, citations)
        
        return {
            'original_response': response,
            'annotated_response': annotated,
            'confidence_analysis': confidence,
            'fact_verification': facts,
            'citation_verification': citations,
            'warnings': warnings,
            'overall_reliability': self._calculate_reliability(
                facts, citations
            )
        }
    
    def _generate_warnings(self, confidence, facts, citations) -> list:
        """Генерирует warnings для пользователя"""
        
        warnings = []
        
        if confidence['overconfidence_markers'] > 2:
            warnings.append(
                "⚠️ Response shows high confidence - verify claims independently"
            )
        
        if facts['verification_rate'] < 0.5:
            warnings.append(
                "⚠️ Less than 50% of claims could be verified"
            )
        
        if citations['fake'] > 0:
            warnings.append(
                f"🚨 {citations['fake']} potentially fake citation(s) detected"
            )
        
        return warnings
```

---

## 5. SENTINEL Integration

```python
class SENTINELMisinformationGuard:
    """SENTINEL модуль защиты от misinformation"""
    
    def __init__(self):
        self.mitigation = MisinformationMitigation()
        self.processor = OutputProcessor()
    
    def protect_request(self, query: str, context: str = None) -> str:
        """Защита на уровне request"""
        
        # Создаём grounded prompt
        return self.mitigation.create_grounded_prompt(query, context)
    
    def protect_response(self, response: str) -> dict:
        """Защита на уровне response"""
        
        result = self.processor.process_response(response)
        
        # Блокируем если reliability слишком низкая
        if result['overall_reliability'] < 0.3:
            return {
                'action': 'block',
                'reason': 'Low reliability score',
                'safe_response': "I cannot provide a reliable answer to this question."
            }
        
        # Добавляем warnings к response
        if result['warnings']:
            result['action'] = 'warn'
        else:
            result['action'] = 'allow'
        
        return result
```

---

## 6. Резюме

| Проблема | Детектирование | Митигация |
|----------|----------------|-----------|
| **Hallucinations** | Confidence analysis | Grounded prompts |
| **Fake citations** | Citation verification | Source checks |
| **Wrong facts** | Fact verification | Knowledge grounding |
| **Overconfidence** | Linguistic markers | Uncertainty requests |

---

## Следующий урок

→ [LLM10: Unbounded Consumption](10-LLM10-unbounded-consumption.md)

---

*AI Security Academy | Track 02: Threat Landscape | OWASP LLM Top 10*
