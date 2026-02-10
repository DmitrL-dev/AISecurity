"""
SafeCrystal v1: Data Integrity Protection
==========================================

Implements safety mechanisms from NIOKR Session 2:
- S-1: Source Traceability
- S-2: Confidence Thresholds
- S-3: Original Context Fallback
- S-4: Verification Pipeline
- S-5: Audit Log
"""

import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict


@dataclass
class SafePrimitive:
    """Primitive with safety metadata."""
    ptype: str
    value: str
    sentence: str
    # Safety fields
    source_offset: int        # Position in original document
    confidence: float         # 0.0 - 1.0
    qualifiers: List[str]     # ["approximate", "estimated", etc.]
    extraction_method: str    # "regex" | "pattern"
    
    def __hash__(self):
        return hash((self.ptype, self.value, self.source_offset))


@dataclass
class SafeResult:
    """Query result with safety metadata."""
    answer: str
    confidence: float
    source_sentence: str
    primitive: Optional[SafePrimitive]
    warnings: List[str] = field(default_factory=list)
    verified: bool = False
    
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


@dataclass
class AuditEntry:
    """Audit log entry."""
    timestamp: datetime
    action: str
    details: Dict


class SafeCrystal:
    """
    Context Crystal with full safety mechanisms.
    """
    
    # Qualifiers that reduce confidence
    UNCERTAINTY_MARKERS = [
        "около", "примерно", "приблизительно", "approximately", "about",
        "возможно", "вероятно", "maybe", "possibly", "perhaps",
        "по оценкам", "estimated", "roughly", "nearly", "almost"
    ]
    
    # Synonyms for query expansion
    SYNONYMS = {
        "ceo": ["ceo", "chief executive", "генеральный директор", "гендиректор"],
        "cto": ["cto", "chief technology", "технический директор", "техдиректор"],
        "revenue": ["revenue", "выручка", "доход", "оборот"],
        "budget": ["budget", "бюджет", "allocation", "финансирование"],
    }
    
    def __init__(self, min_confidence: float = 0.7, warn_confidence: float = 0.85):
        self.primitives: List[SafePrimitive] = []
        self.original_text: str = ""
        self.word_index: Dict[str, List[int]] = defaultdict(list)
        self.audit_log: List[AuditEntry] = []
        self.min_confidence = min_confidence
        self.warn_confidence = warn_confidence
    
    def _log(self, action: str, details: Dict):
        """Add audit log entry."""
        self.audit_log.append(AuditEntry(
            timestamp=datetime.now(),
            action=action,
            details=details
        ))
    
    def _calculate_confidence(self, sentence: str, value: str) -> Tuple[float, List[str]]:
        """Calculate confidence based on text markers."""
        confidence = 1.0
        qualifiers = []
        
        sentence_lower = sentence.lower()
        
        for marker in self.UNCERTAINTY_MARKERS:
            if marker in sentence_lower:
                confidence *= 0.7
                qualifiers.append(marker)
        
        # Check if value is directly quoted or inferred
        if value.lower() in sentence.lower():
            confidence *= 1.0  # Direct match
        else:
            confidence *= 0.8  # Inferred
            qualifiers.append("inferred")
        
        return min(confidence, 1.0), qualifiers
    
    def _extract_primitives(self, text: str) -> List[SafePrimitive]:
        """Extract primitives with safety metadata."""
        primitives = []
        # Split on sentence-ending punctuation followed by space and capital letter
        # This avoids splitting on IP addresses like 192.168.1.100
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        offset = 0
        
        for sent in sentences:
            sent_offset = text.find(sent, offset)
            offset = sent_offset + len(sent)
            
            # Money extraction
            money_matches = re.findall(r'(\$[\d,.]+\s*(?:billion|million|млрд|млн)?)', sent, re.I)
            for money in money_matches:
                conf, quals = self._calculate_confidence(sent, money)
                primitives.append(SafePrimitive(
                    ptype="MONEY",
                    value=money,
                    sentence=sent,
                    source_offset=sent_offset,
                    confidence=conf,
                    qualifiers=quals,
                    extraction_method="regex"
                ))
            
            # Person + Role extraction
            role_patterns = [
                (r'CEO\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'ROLE_CEO'),
                (r'CTO\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'ROLE_CTO'),
                (r'Chief Technology Officer\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'ROLE_CTO'),
            ]
            for pattern, ptype in role_patterns:
                matches = re.findall(pattern, sent)
                for name in matches:
                    conf, quals = self._calculate_confidence(sent, name)
                    primitives.append(SafePrimitive(
                        ptype=ptype,
                        value=name,
                        sentence=sent,
                        source_offset=sent_offset,
                        confidence=conf,
                        qualifiers=quals,
                        extraction_method="pattern"
                    ))
            
            # IP extraction
            ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', sent)
            for ip in ips:
                conf, quals = self._calculate_confidence(sent, ip)
                primitives.append(SafePrimitive(
                    ptype="IP",
                    value=ip,
                    sentence=sent,
                    source_offset=sent_offset,
                    confidence=conf,
                    qualifiers=quals,
                    extraction_method="regex"
                ))
            
            # Percentage extraction
            pcts = re.findall(r'(\d+(?:\.\d+)?%)', sent)
            for pct in pcts:
                conf, quals = self._calculate_confidence(sent, pct)
                primitives.append(SafePrimitive(
                    ptype="PERCENT",
                    value=pct,
                    sentence=sent,
                    source_offset=sent_offset,
                    confidence=conf,
                    qualifiers=quals,
                    extraction_method="regex"
                ))
            
            # Date extraction
            dates = re.findall(r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4})', sent)
            for date in dates:
                conf, quals = self._calculate_confidence(sent, date)
                primitives.append(SafePrimitive(
                    ptype="DATE",
                    value=date,
                    sentence=sent,
                    source_offset=sent_offset,
                    confidence=conf,
                    qualifiers=quals,
                    extraction_method="regex"
                ))
            
            # Codename extraction
            codes = re.findall(r'codenamed?\s+([A-Z]{3,})', sent, re.I)
            for code in codes:
                conf, quals = self._calculate_confidence(sent, code)
                primitives.append(SafePrimitive(
                    ptype="CODENAME",
                    value=code,
                    sentence=sent,
                    source_offset=sent_offset,
                    confidence=conf,
                    qualifiers=quals,
                    extraction_method="pattern"
                ))
        
        return primitives
    
    def build(self, text: str) -> 'SafeCrystal':
        """Build crystal with full safety tracking."""
        self.original_text = text
        self.primitives = self._extract_primitives(text)
        
        # Build index
        for i, prim in enumerate(self.primitives):
            for word in prim.value.lower().split():
                self.word_index[word].append(i)
            self.word_index[prim.ptype.lower()].append(i)
            # Add type-specific keywords
            if prim.ptype == "IP":
                self.word_index["ip"].append(i)
                self.word_index["server"].append(i)
                self.word_index["address"].append(i)
            elif prim.ptype == "MONEY":
                self.word_index["revenue"].append(i)
                self.word_index["budget"].append(i)
                self.word_index["money"].append(i)
                self.word_index["billion"].append(i)
                self.word_index["million"].append(i)
        
        # Log
        self._log("build", {
            "text_length": len(text),
            "primitives_extracted": len(self.primitives),
            "avg_confidence": sum(p.confidence for p in self.primitives) / len(self.primitives) if self.primitives else 0
        })
        
        return self
    
    def _expand_query(self, q: str) -> Set[str]:
        """Expand query with synonyms."""
        words = set(q.lower().split())
        expanded = set(words)
        for word in words:
            for key, syns in self.SYNONYMS.items():
                if word in syns or key in word:
                    expanded.update(syns)
        return expanded
    
    def _verify_in_source(self, prim: SafePrimitive) -> bool:
        """Verify primitive exists in original text."""
        return prim.sentence in self.original_text
    
    def _naive_search(self, q: str) -> str:
        """Fallback to naive text search."""
        sentences = re.split(r'[.!?]\s+', self.original_text)
        q_words = set(q.lower().split())
        
        best_score = 0
        best_sent = ""
        for sent in sentences:
            score = sum(1 for w in q_words if w in sent.lower())
            if score > best_score:
                best_score = score
                best_sent = sent
        
        return best_sent
    
    def query(self, q: str) -> SafeResult:
        """Query with full safety verification."""
        expanded = self._expand_query(q)
        
        # Score primitives
        scores = defaultdict(int)
        for word in expanded:
            for idx in self.word_index.get(word, []):
                scores[idx] += 1
        
        if not scores:
            # Fallback to naive search
            fallback = self._naive_search(q)
            self._log("query_fallback", {"query": q, "reason": "no_primitives_matched"})
            return SafeResult(
                answer=fallback,
                confidence=0.5,
                source_sentence=fallback,
                primitive=None,
                warnings=["Fallback to text search - no primitives matched"],
                verified=False
            )
        
        # Get best primitive
        best_idx = max(scores.keys(), key=lambda x: (scores[x], self.primitives[x].confidence))
        best_prim = self.primitives[best_idx]
        
        # Verify in source
        verified = self._verify_in_source(best_prim)
        
        # Build warnings
        warnings = []
        if best_prim.confidence < self.warn_confidence:
            warnings.append(f"Low confidence: {best_prim.confidence:.0%}")
        if best_prim.qualifiers:
            warnings.append(f"Qualifiers: {', '.join(best_prim.qualifiers)}")
        if not verified:
            warnings.append("Could not verify in source text")
        
        # Check minimum confidence
        if best_prim.confidence < self.min_confidence:
            fallback = self._naive_search(q)
            self._log("query_low_confidence", {
                "query": q,
                "primitive_confidence": best_prim.confidence,
                "fallback_used": True
            })
            return SafeResult(
                answer=fallback,
                confidence=0.5,
                source_sentence=fallback,
                primitive=best_prim,
                warnings=warnings + ["Below minimum confidence, using fallback"],
                verified=False
            )
        
        self._log("query_success", {
            "query": q,
            "primitive": best_prim.value,
            "confidence": best_prim.confidence,
            "verified": verified
        })
        
        return SafeResult(
            answer=best_prim.sentence,
            confidence=best_prim.confidence,
            source_sentence=best_prim.sentence,
            primitive=best_prim,
            warnings=warnings,
            verified=verified
        )
    
    def get_audit_log(self) -> List[Dict]:
        """Get audit log for inspection."""
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                **e.details
            }
            for e in self.audit_log
        ]


# =============================================================================
# TEST SUITE
# =============================================================================

def run_safety_tests():
    """Run safety verification tests."""
    
    print("=" * 60)
    print("SAFECRISTAL SAFETY TESTS")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Source Traceability
    print("\n[Test 1] Source Traceability")
    crystal = SafeCrystal().build("The CEO is John Smith.")
    for prim in crystal.primitives:
        tests_total += 1
        if prim.sentence in crystal.original_text:
            print(f"  ✓ Primitive '{prim.value}' traceable")
            tests_passed += 1
        else:
            print(f"  ✗ Primitive '{prim.value}' NOT traceable")
    
    # Test 2: Confidence Scoring for Uncertain Data
    print("\n[Test 2] Confidence Scoring")
    crystal = SafeCrystal().build("Revenue was approximately $2.5 billion.")
    tests_total += 1
    for prim in crystal.primitives:
        if prim.ptype == "MONEY":
            if prim.confidence < 1.0 and "approximately" in prim.qualifiers:
                print(f"  ✓ Uncertain data flagged: conf={prim.confidence:.0%}, quals={prim.qualifiers}")
                tests_passed += 1
            else:
                print(f"  ✗ Uncertain data NOT flagged")
    
    # Test 3: Fallback on No Match
    print("\n[Test 3] Fallback on No Match")
    crystal = SafeCrystal().build("The CEO is John.")
    result = crystal.query("What is the server IP?")
    tests_total += 1
    if "Fallback" in result.warnings[0] if result.warnings else False:
        print(f"  ✓ Fallback used correctly")
        tests_passed += 1
    else:
        print(f"  ✗ Fallback not triggered")
    
    # Test 4: Verification Pipeline
    print("\n[Test 4] Verification Pipeline")
    crystal = SafeCrystal().build("The company revenue is $5 billion this year.")
    result = crystal.query("What is the revenue?")
    tests_total += 1
    if result.verified and result.primitive is not None:
        print(f"  ✓ Result verified: {result.primitive.value}")
        tests_passed += 1
    else:
        print(f"  ✗ Result not verified (primitive={result.primitive})")
    
    # Test 5: Audit Log
    print("\n[Test 5] Audit Log")
    crystal = SafeCrystal().build("Test document.")
    crystal.query("test query")
    audit = crystal.get_audit_log()
    tests_total += 1
    if len(audit) >= 2:  # build + query
        print(f"  ✓ Audit log has {len(audit)} entries")
        tests_passed += 1
    else:
        print(f"  ✗ Audit log incomplete: {len(audit)} entries")
    
    # Test 6: Low Confidence Warning
    print("\n[Test 6] Low Confidence Warning")
    crystal = SafeCrystal(warn_confidence=0.9).build("Maybe the CEO is probably John, approximately.")
    result = crystal.query("Who is CEO?")
    tests_total += 1
    if result.has_warnings():
        print(f"  ✓ Warnings generated: {result.warnings}")
        tests_passed += 1
    else:
        print(f"  ✗ No warnings for uncertain data")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("=" * 60)
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = run_safety_tests()
    
    if success:
        print("\n✅ All safety mechanisms working!")
    else:
        print("\n⚠️ Some safety tests failed")
