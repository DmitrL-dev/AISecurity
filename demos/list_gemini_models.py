#!/usr/bin/env python3
"""List available Gemini API models."""
import os

try:
    import google.generativeai as genai
except ImportError:
    print("Install: pip install google-generativeai")
    exit(1)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Set GEMINI_API_KEY environment variable")
    exit(1)

genai.configure(api_key=api_key)

print("Available Gemini Models:\n")
for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(f"  {model.name}")
