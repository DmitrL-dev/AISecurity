"""
Example: Document Analysis
==========================

Analyze a large document with RLM.
"""

from pathlib import Path
from rlm_toolkit import RLM, RLMConfig

def main():
    # Configuration with cost controls
    config = RLMConfig(
        max_iterations=50,
        max_cost=5.0,  # Max $5 per run
    )
    
    # Create RLM with OpenAI
    rlm = RLM.from_openai("gpt-4o", config=config)
    
    # Load document (can be very large)
    doc_path = Path("sample_document.txt")
    if not doc_path.exists():
        # Create sample document for demo
        doc_path.write_text("""
        QUARTERLY FINANCIAL REPORT Q4 2025
        
        Executive Summary:
        Revenue increased by 15% compared to Q3, reaching $2.5B.
        Operating costs decreased by 8% due to efficiency improvements.
        Net profit margin improved to 23%.
        
        Key Metrics:
        - Total Revenue: $2,500,000,000
        - Operating Costs: $1,750,000,000
        - Net Profit: $575,000,000
        - Customer Acquisition: 125,000 new customers
        - Customer Retention: 94%
        
        Regional Performance:
        - North America: 45% of revenue
        - Europe: 30% of revenue
        - Asia Pacific: 20% of revenue
        - Other: 5% of revenue
        
        Outlook:
        Q1 2026 is projected to show continued growth with
        expected revenue of $2.7B based on current trends.
        """)
    
    context = doc_path.read_text()
    
    # Analyze with multiple questions
    questions = [
        "What was the total revenue and net profit?",
        "Which region had the highest contribution?",
        "What is the projected revenue for Q1 2026?",
    ]
    
    for query in questions:
        print(f"\nQ: {query}")
        result = rlm.run(context=context, query=query)
        print(f"A: {result.answer}")
        print(f"   Cost: ${result.total_cost:.4f}")


if __name__ == "__main__":
    main()
