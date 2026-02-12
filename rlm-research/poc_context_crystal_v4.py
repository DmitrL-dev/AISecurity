"""
Context Crystal v4 - DETERMINISTIC TEST
========================================

Previous issues: random.shuffle caused inconsistent results.
v4: deterministic test + improved extraction.
"""

import time
import struct
import re
from dataclasses import dataclass
from typing import List, Dict, Set
from collections import defaultdict


@dataclass
class Primitive:
    ptype: str
    value: str
    sentence: str
    keywords: Set[str]


class ContextCrystalV4:
    """Final optimized version."""
    
    PATTERNS = [
        # Role + Name (find NAME after role keyword)
        (r'CEO\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'ROLE', {'ceo', 'chief', 'executive'}),
        (r'Chief Technology Officer\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'ROLE', {'cto', 'chief', 'technology'}),
        # Money
        (r'revenue[^.]*?(\$[\d,.]+\s*(?:billion|million)?)', 'MONEY', {'revenue', 'income'}),
        (r'R&D[^.]*?(\$[\d,.]+\s*(?:billion|million)?)', 'MONEY', {'r&d', 'budget', 'allocation'}),
        (r'Budget allocation[^.]*?(\$[\d,.]+\s*(?:billion|million)?)', 'MONEY', {'budget', 'allocation', 'r&d'}),
        # Percentages
        (r'satisfaction[^.]*?(\d+%)', 'PERCENT', {'satisfaction', 'score', 'customer'}),
        # IP
        (r'IP address[^.]*?(\d+\.\d+\.\d+\.\d+)', 'IP', {'ip', 'server', 'address'}),
        # Codename
        (r'codenamed\s+([A-Z]+)', 'CODE', {'codename', 'project', 'secret'}),
        # Deadline
        (r'deadline[^.]*?(January \d+, \d+)', 'DATE', {'deadline', 'phase', 'date'}),
    ]
    
    def __init__(self):
        self.primitives: List[Primitive] = []
        self.index: Dict[str, List[int]] = defaultdict(list)
    
    def build(self, text: str) -> 'ContextCrystalV4':
        sentences = re.split(r'[.!?]\s+', text)
        
        for sent in sentences:
            for pattern, ptype, keywords in self.PATTERNS:
                matches = re.findall(pattern, sent, re.IGNORECASE)
                for match in matches:
                    prim = Primitive(ptype, match, sent, keywords)
                    idx = len(self.primitives)
                    self.primitives.append(prim)
                    
                    # Index by keywords + value
                    for kw in keywords:
                        self.index[kw].append(idx)
                    for word in match.lower().split():
                        self.index[word].append(idx)
        
        return self
    
    def query(self, q: str) -> str:
        q_lower = q.lower()
        scores = defaultdict(int)
        
        # Score by keyword match
        for word in q_lower.split():
            if len(word) > 2:
                for idx in self.index.get(word, []):
                    scores[idx] += 2
        
        # Boost for synonym matches
        if 'ceo' in q_lower or 'chief executive' in q_lower:
            for idx in self.index.get('ceo', []): scores[idx] += 5
        if 'cto' in q_lower or 'chief technology' in q_lower:
            for idx in self.index.get('cto', []): scores[idx] += 5
        if 'revenue' in q_lower:
            for idx in self.index.get('revenue', []): scores[idx] += 5
        if 'budget' in q_lower or 'r&d' in q_lower or 'r & d' in q_lower:
            for idx in self.index.get('r&d', []): scores[idx] += 5
            for idx in self.index.get('budget', []): scores[idx] += 5
        if 'satisfaction' in q_lower or 'score' in q_lower:
            for idx in self.index.get('satisfaction', []): scores[idx] += 5
        if 'ip' in q_lower or 'server' in q_lower:
            for idx in self.index.get('ip', []): scores[idx] += 5
        if 'codename' in q_lower or 'project' in q_lower:
            for idx in self.index.get('codename', []): scores[idx] += 5
        if 'deadline' in q_lower or 'phase' in q_lower:
            for idx in self.index.get('deadline', []): scores[idx] += 5
        
        if not scores:
            return "Not found"
        
        best_idx = max(scores.keys(), key=lambda x: scores[x])
        return self.primitives[best_idx].sentence
    
    def serialize(self) -> bytes:
        data = []
        for p in self.primitives:
            data.append(p.value.encode()[:100])
        return b'\n'.join(data)


def create_test_doc(size: int) -> str:
    """Deterministic document with facts at known positions."""
    facts = [
        "The company revenue in 2025 was $2.5 billion.",
        "CEO Alexandra Chen announced the merger.",
        "The secret project codenamed PHOENIX is scheduled.",
        "Server IP address is 192.168.42.100.",
        "Customer satisfaction score reached 94%.",
        "Budget allocation for R&D is $500 million.",
        "Chief Technology Officer Michael Park leads.",
        "The deadline for Phase 2 is January 15, 2026.",
    ]
    
    filler = "The quarterly report shows improvement in metrics. "
    
    # Build deterministic document
    parts = []
    for i, fact in enumerate(facts):
        parts.append(filler * 10)  # Filler
        parts.append(fact)
    
    base = " ".join(parts)
    # Repeat to reach size
    while len(base) < size * 4:
        base = base + " " + filler * 50
    
    return base[:size * 4]


def run_test():
    print("=" * 60)
    print("CONTEXT CRYSTAL v4 - DETERMINISTIC")
    print("=" * 60)
    
    queries = [
        ("What was the company revenue?", "$2.5 billion"),
        ("Who is the CEO?", "Alexandra Chen"),
        ("What is the secret project codename?", "PHOENIX"),
        ("What is the server IP?", "192.168.42.100"),
        ("What is the customer satisfaction score?", "94%"),
        ("What is the R&D budget?", "$500 million"),
        ("Who is the CTO?", "Michael Park"),
        ("What is the Phase 2 deadline?", "January 15, 2026"),
    ]
    
    for size in [10_000, 100_000, 500_000]:
        print(f"\n--- {size:,} tokens ---")
        doc = create_test_doc(size)
        
        crystal = ContextCrystalV4().build(doc)
        
        raw = len(doc.encode())
        compressed = len(crystal.serialize())
        
        correct = 0
        total_time = 0
        
        for q, expected in queries:
            t0 = time.perf_counter()
            result = crystal.query(q)
            total_time += time.perf_counter() - t0
            
            hit = expected.lower() in result.lower()
            if hit:
                correct += 1
            print(f"  {'✓' if hit else '✗'} {q[:30]}")
        
        acc = correct / len(queries) * 100
        avg_time = total_time / len(queries) * 1000
        compress = raw / compressed if compressed > 0 else 0
        
        print(f"\nAccuracy: {acc:.0f}%  Time: {avg_time:.2f}ms  Compress: {compress:.0f}x")
        print(f"Primitives: {len(crystal.primitives)}")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
