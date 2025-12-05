#!/usr/bin/env python3
"""Test API mode with documents."""
import os
import sys

# Set environment
os.environ['LLM_PROVIDER'] = 'api'
os.environ['HF_API_BASE_URL'] = 'https://davidtran999-hue-portal-backend.hf.space/api'

# Add path
sys.path.insert(0, 'hue_portal')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hue_portal.settings')
import django
django.setup()

from hue_portal.chatbot.llm_integration import get_llm_generator
from hue_portal.core.models import Fine

# Get LLM
llm = get_llm_generator()
print(f"✅ LLM Provider: {llm.provider}")
print(f"✅ API URL: {llm.api_base_url}")
print(f"✅ Available: {llm.is_available()}\n")

# Get some documents
fines = Fine.objects.all()[:3]
print(f"📄 Found {len(fines)} documents\n")

# Test with documents
query = "Mức phạt vượt đèn đỏ là bao nhiêu?"
print(f"❓ Query: {query}\n")

# Build prompt
prompt = llm._build_prompt(query, None, list(fines))
print(f"📝 Prompt length: {len(prompt)} chars")
print(f"📝 Prompt preview:\n{prompt[:500]}...\n")

# Test API call
print("🔗 Calling HF Spaces API...\n")
result = llm._generate_api(prompt, None)

if result:
    print(f"✅ Success! Response length: {len(result)}")
    print(f"📥 Response:\n{result[:500]}...\n")
else:
    print("❌ No response from API\n")




