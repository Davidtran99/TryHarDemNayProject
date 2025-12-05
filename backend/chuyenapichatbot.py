#!/usr/bin/env python3
"""
Script để chuyển đổi API chatbot giữa các mode:
- api: Gọi HF Spaces API (mặc định)
- local: Dùng local model
- llama_cpp: Dùng llama.cpp model
- openai: Dùng OpenAI API
- anthropic: Dùng Anthropic Claude API
- ollama: Dùng Ollama local
"""
import os
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text: str, color: str = Colors.RESET):
    """Print colored text."""
    print(f"{color}{text}{Colors.RESET}")

def get_env_file():
    """Get .env file path."""
    backend_dir = Path(__file__).parent
    env_file = backend_dir / ".env"
    return env_file

def read_env_file():
    """Read .env file and return as dict."""
    env_file = get_env_file()
    env_vars = {}
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

def write_env_file(env_vars: dict):
    """Write .env file from dict."""
    env_file = get_env_file()
    
    # Read existing file to preserve comments and order
    existing_lines = []
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()
    
    # Update or add LLM_PROVIDER and HF_API_BASE_URL
    new_lines = []
    llm_provider_set = False
    hf_api_base_set = False
    
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith('LLM_PROVIDER='):
            new_lines.append(f"LLM_PROVIDER={env_vars.get('LLM_PROVIDER', 'api')}\n")
            llm_provider_set = True
        elif stripped.startswith('HF_API_BASE_URL='):
            new_lines.append(f"HF_API_BASE_URL={env_vars.get('HF_API_BASE_URL', 'https://davidtran999-hue-portal-backend.hf.space/api')}\n")
            hf_api_base_set = True
        else:
            new_lines.append(line)
    
    # Add if not found
    if not llm_provider_set:
        new_lines.append(f"LLM_PROVIDER={env_vars.get('LLM_PROVIDER', 'api')}\n")
    if not hf_api_base_set and env_vars.get('LLM_PROVIDER') == 'api':
        new_lines.append(f"HF_API_BASE_URL={env_vars.get('HF_API_BASE_URL', 'https://davidtran999-hue-portal-backend.hf.space/api')}\n")
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def show_current():
    """Show current LLM provider configuration."""
    env_vars = read_env_file()
    provider = env_vars.get('LLM_PROVIDER', 'api')
    api_url = env_vars.get('HF_API_BASE_URL', 'https://davidtran999-hue-portal-backend.hf.space/api')
    
    print_colored("\n📊 Cấu hình hiện tại:", Colors.BOLD)
    print_colored(f"   Provider: {provider}", Colors.CYAN)
    if provider == 'api':
        print_colored(f"   API URL: {api_url}", Colors.CYAN)
    print()

def switch_provider(provider: str, api_url: str = None):
    """Switch LLM provider."""
    env_vars = read_env_file()
    
    valid_providers = ['api', 'local', 'llama_cpp', 'openai', 'anthropic', 'ollama', 'huggingface']
    
    if provider not in valid_providers:
        print_colored(f"❌ Provider không hợp lệ: {provider}", Colors.RED)
        print_colored(f"   Các provider hợp lệ: {', '.join(valid_providers)}", Colors.YELLOW)
        return False
    
    env_vars['LLM_PROVIDER'] = provider
    
    if provider == 'api':
        if api_url:
            env_vars['HF_API_BASE_URL'] = api_url
        elif 'HF_API_BASE_URL' not in env_vars:
            env_vars['HF_API_BASE_URL'] = 'https://davidtran999-hue-portal-backend.hf.space/api'
        print_colored(f"✅ Đã chuyển sang API mode (HF Spaces)", Colors.GREEN)
        print_colored(f"   API URL: {env_vars['HF_API_BASE_URL']}", Colors.CYAN)
    elif provider == 'local':
        print_colored(f"✅ Đã chuyển sang Local model mode", Colors.GREEN)
    elif provider == 'llama_cpp':
        print_colored(f"✅ Đã chuyển sang llama.cpp mode", Colors.GREEN)
    elif provider == 'openai':
        print_colored(f"✅ Đã chuyển sang OpenAI mode", Colors.GREEN)
    elif provider == 'anthropic':
        print_colored(f"✅ Đã chuyển sang Anthropic Claude mode", Colors.GREEN)
    elif provider == 'ollama':
        print_colored(f"✅ Đã chuyển sang Ollama mode", Colors.GREEN)
    elif provider == 'huggingface':
        print_colored(f"✅ Đã chuyển sang Hugging Face Inference API mode", Colors.GREEN)
    
    write_env_file(env_vars)
    print_colored("\n⚠️  Cần restart backend server để áp dụng thay đổi!", Colors.YELLOW)
    return True

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print_colored("\n🔧 Script chuyển đổi API Chatbot", Colors.BOLD)
        print_colored("=" * 50, Colors.CYAN)
        print_colored("\nCách sử dụng:", Colors.BOLD)
        print_colored("  python chuyenapichatbot.py <provider> [api_url]", Colors.YELLOW)
        print_colored("\nCác provider:", Colors.BOLD)
        print_colored("  api         - Gọi HF Spaces API (mặc định)", Colors.GREEN)
        print_colored("  local       - Dùng local model", Colors.CYAN)
        print_colored("  llama_cpp   - Dùng llama.cpp model", Colors.CYAN)
        print_colored("  openai      - Dùng OpenAI API", Colors.CYAN)
        print_colored("  anthropic   - Dùng Anthropic Claude API", Colors.CYAN)
        print_colored("  ollama      - Dùng Ollama local", Colors.CYAN)
        print_colored("  huggingface - Dùng Hugging Face Inference API", Colors.CYAN)
        print_colored("\nVí dụ:", Colors.BOLD)
        print_colored("  python chuyenapichatbot.py api", Colors.YELLOW)
        print_colored("  python chuyenapichatbot.py api https://custom-api.hf.space/api", Colors.YELLOW)
        print_colored("  python chuyenapichatbot.py local", Colors.YELLOW)
        print_colored("  python chuyenapichatbot.py current  # Xem cấu hình hiện tại", Colors.YELLOW)
        print()
        show_current()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'current' or command == 'show':
        show_current()
        return
    
    provider = command
    api_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    switch_provider(provider, api_url)

if __name__ == "__main__":
    main()


