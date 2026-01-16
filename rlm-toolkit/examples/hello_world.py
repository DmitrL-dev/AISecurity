"""
Example: Hello World
====================

Basic RLM usage with Ollama.
"""

from rlm_toolkit import RLM

def main():
    # Create RLM with local Ollama
    rlm = RLM.from_ollama("llama3")
    
    # Simple context
    context = """
    The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars
    in Paris, France. It is named after the engineer Gustave Eiffel, whose
    company designed and built the tower from 1887 to 1889.
    
    The tower is 330 metres (1,083 ft) tall, about the same height as an
    81-storey building. It was the tallest man-made structure in the world
    for 41 years until the Chrysler Building in New York City was finished in 1930.
    """
    
    # Run query
    result = rlm.run(
        context=context,
        query="How tall is the Eiffel Tower and when was it built?"
    )
    
    print("Answer:", result.answer)
    print(f"Iterations: {result.iterations}")
    print(f"Cost: ${result.total_cost:.4f}")


if __name__ == "__main__":
    main()
