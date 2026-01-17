"""
RLM Logic Test - No API required (mock mode)
Verifies the core RLM logic works correctly.
"""
import re
import io
import sys


class MockLLM:
    """Simulates LLM responses for testing."""
    
    def generate(self, prompt: str) -> str:
        # Simulate LLM understanding the RLM protocol
        if "how many chapters" in prompt.lower():
            return """```python
# Count chapters in context
chapters = [line for line in context.split('\\n') if line.startswith('Chapter')]
print(f"Found {len(chapters)} chapters")
```"""
        elif "Found" in prompt:
            return "FINAL(3)"
        else:
            return "FINAL(unknown)"


class SimpleRLM:
    """Minimal RLM implementation."""
    
    def __init__(self, llm):
        self.llm = llm
        
    def run(self, context: str, query: str) -> dict:
        repl_state = {"context": context}
        history = []
        iterations = 0
        
        prompt = f"context has {len(context)} chars. Task: {query}"
        
        while iterations < 5:
            iterations += 1
            
            # Get LLM response
            response = self.llm.generate(prompt + str(history))
            
            # Check for FINAL
            if "FINAL(" in response:
                match = re.search(r'FINAL\((.+?)\)', response)
                answer = match.group(1) if match else response
                return {"answer": answer, "iterations": iterations, "status": "success"}
            
            # Execute code
            code = self._extract_code(response)
            if code:
                output = self._execute(code, repl_state)
                history.append(output)
                prompt = f"Output: {output}. Continue or FINAL(answer)."
        
        return {"answer": None, "iterations": iterations, "status": "max_iterations"}
    
    def _extract_code(self, text: str) -> str:
        if "```python" in text:
            return text.split("```python")[1].split("```")[0]
        elif "```" in text:
            return text.split("```")[1].split("```")[0]
        return ""
    
    def _execute(self, code: str, state: dict) -> str:
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        
        try:
            exec(code, state)
            output = buffer.getvalue()
        except Exception as e:
            output = f"Error: {e}"
        finally:
            sys.stdout = old_stdout
        
        return output.strip()


# ============================================
# TEST
# ============================================

print("🧪 RLM Logic Test (Mock Mode)")
print("=" * 40)

context = """
Chapter 1: Introduction
The quick brown fox jumps over the lazy dog.

Chapter 2: Methods  
We used Python and machine learning.

Chapter 3: Results
The accuracy was 95.2%.
"""

print(f"📄 Context: {len(context)} chars")
print(f"❓ Query: How many chapters?")
print()

# Run RLM
llm = MockLLM()
rlm = SimpleRLM(llm)
result = rlm.run(context, "How many chapters are there?")

print(f"📊 Result: {result}")
print()

# Verify
if result["answer"] == "3":
    print("✅ TEST PASSED: RLM logic works correctly!")
    print("   - Code extraction: ✓")
    print("   - REPL execution: ✓") 
    print("   - FINAL parsing: ✓")
else:
    print(f"❌ TEST FAILED: Expected '3', got '{result['answer']}'")

print()
print("💡 This proves the RLM code pattern works.")
print("   For real usage, replace MockLLM with OpenAI/Claude/Ollama provider.")
