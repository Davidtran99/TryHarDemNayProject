#!/usr/bin/env python3
"""
Script để thay đổi LLM provider linh hoạt.
Sử dụng: python switch_llm_provider.py [provider] [options]
"""
import os
import sys
import argparse
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color=Colors.RESET):
    """Print colored text."""
    print(f"{color}{text}{Colors.RESET}")

def get_env_file():
    """Get .env file path."""
    # Try multiple locations
    possible_paths = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path.home() / ".env",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # Return default location
    return Path(__file__).parent / ".env"

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
    
    return env_vars, env_file

def write_env_file(env_vars, env_file):
    """Write .env file from dict."""
    # Read existing file to preserve comments and order
    lines = []
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # Create new content
    new_lines = []
    llm_provider_set = False
    local_model_vars_set = set()
    
    # Track which LLM-related vars we've set
    llm_related_vars = {
        'LLM_PROVIDER', 'LOCAL_MODEL_PATH', 'LOCAL_MODEL_DEVICE',
        'LOCAL_MODEL_4BIT', 'LOCAL_MODEL_8BIT', 'HF_API_BASE_URL',
        'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OLLAMA_BASE_URL', 'OLLAMA_MODEL'
    }
    
    # Process existing lines
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            new_lines.append(line)
            continue
        
        if '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in llm_related_vars:
                # Skip old LLM-related vars, we'll add new ones
                if key == 'LLM_PROVIDER':
                    llm_provider_set = True
                if key.startswith('LOCAL_MODEL_'):
                    local_model_vars_set.add(key)
                continue
        
        new_lines.append(line)
    
    # Add LLM provider config
    if not llm_provider_set:
        new_lines.append("\n# LLM Provider Configuration\n")
    
    provider = env_vars.get('LLM_PROVIDER', 'none')
    new_lines.append(f"LLM_PROVIDER={provider}\n")
    
    # Add provider-specific configs
    if provider == 'local':
        new_lines.append(f"LOCAL_MODEL_PATH={env_vars.get('LOCAL_MODEL_PATH', 'Qwen/Qwen2.5-7B-Instruct')}\n")
        new_lines.append(f"LOCAL_MODEL_DEVICE={env_vars.get('LOCAL_MODEL_DEVICE', 'auto')}\n")
        new_lines.append(f"LOCAL_MODEL_8BIT={env_vars.get('LOCAL_MODEL_8BIT', 'true')}\n")
        new_lines.append(f"LOCAL_MODEL_4BIT={env_vars.get('LOCAL_MODEL_4BIT', 'false')}\n")
    elif provider == 'api':
        new_lines.append(f"HF_API_BASE_URL={env_vars.get('HF_API_BASE_URL', 'https://davidtran999-hue-portal-backend.hf.space/api')}\n")
    elif provider == 'openai':
        if 'OPENAI_API_KEY' in env_vars:
            new_lines.append(f"OPENAI_API_KEY={env_vars['OPENAI_API_KEY']}\n")
    elif provider == 'anthropic':
        if 'ANTHROPIC_API_KEY' in env_vars:
            new_lines.append(f"ANTHROPIC_API_KEY={env_vars['ANTHROPIC_API_KEY']}\n")
    elif provider == 'ollama':
        new_lines.append(f"OLLAMA_BASE_URL={env_vars.get('OLLAMA_BASE_URL', 'http://localhost:11434')}\n")
        new_lines.append(f"OLLAMA_MODEL={env_vars.get('OLLAMA_MODEL', 'qwen2.5:7b')}\n")
    
    # Write to file
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return env_file

def set_provider(provider, **kwargs):
    """Set LLM provider and related config."""
    env_vars, env_file = read_env_file()
    
    # Update provider
    env_vars['LLM_PROVIDER'] = provider
    
    # Update provider-specific configs
    if provider == 'local':
        env_vars['LOCAL_MODEL_PATH'] = kwargs.get('model_path', 'Qwen/Qwen2.5-7B-Instruct')
        env_vars['LOCAL_MODEL_DEVICE'] = kwargs.get('device', 'auto')
        env_vars['LOCAL_MODEL_8BIT'] = kwargs.get('use_8bit', 'true')
        env_vars['LOCAL_MODEL_4BIT'] = kwargs.get('use_4bit', 'false')
    elif provider == 'api':
        env_vars['HF_API_BASE_URL'] = kwargs.get('api_url', 'https://davidtran999-hue-portal-backend.hf.space/api')
    
    # Write to file
    write_env_file(env_vars, env_file)
    
    print_colored(f"✅ Đã chuyển sang LLM Provider: {provider.upper()}", Colors.GREEN)
    print_colored(f"📝 File: {env_file}", Colors.BLUE)
    
    if provider == 'local':
        print_colored(f"   Model: {env_vars['LOCAL_MODEL_PATH']}", Colors.BLUE)
        print_colored(f"   Device: {env_vars['LOCAL_MODEL_DEVICE']}", Colors.BLUE)
        print_colored(f"   8-bit: {env_vars['LOCAL_MODEL_8BIT']}", Colors.BLUE)
        print_colored(f"   4-bit: {env_vars['LOCAL_MODEL_4BIT']}", Colors.BLUE)
    elif provider == 'api':
        print_colored(f"   API URL: {env_vars['HF_API_BASE_URL']}", Colors.BLUE)
    
    return env_file

def show_current():
    """Show current LLM provider configuration."""
    env_vars, env_file = read_env_file()
    
    provider = env_vars.get('LLM_PROVIDER', 'none')
    
    print_colored("\n" + "="*60, Colors.BOLD)
    print_colored("Current LLM Provider Configuration", Colors.BOLD)
    print_colored("="*60, Colors.RESET)
    print_colored(f"Provider: {provider.upper()}", Colors.GREEN)
    print_colored(f"Config file: {env_file}", Colors.BLUE)
    
    if provider == 'local':
        print_colored("\nLocal Model Settings:", Colors.YELLOW)
        print(f"  MODEL_PATH: {env_vars.get('LOCAL_MODEL_PATH', 'Qwen/Qwen2.5-7B-Instruct')}")
        print(f"  DEVICE: {env_vars.get('LOCAL_MODEL_DEVICE', 'auto')}")
        print(f"  8BIT: {env_vars.get('LOCAL_MODEL_8BIT', 'true')}")
        print(f"  4BIT: {env_vars.get('LOCAL_MODEL_4BIT', 'false')}")
    elif provider == 'api':
        print_colored("\nAPI Mode Settings:", Colors.YELLOW)
        print(f"  API_URL: {env_vars.get('HF_API_BASE_URL', 'https://davidtran999-hue-portal-backend.hf.space/api')}")
    elif provider == 'openai':
        has_key = 'OPENAI_API_KEY' in env_vars and env_vars['OPENAI_API_KEY']
        print_colored(f"\nOpenAI Settings:", Colors.YELLOW)
        print(f"  API_KEY: {'✅ Set' if has_key else '❌ Not set'}")
    elif provider == 'anthropic':
        has_key = 'ANTHROPIC_API_KEY' in env_vars and env_vars['ANTHROPIC_API_KEY']
        print_colored(f"\nAnthropic Settings:", Colors.YELLOW)
        print(f"  API_KEY: {'✅ Set' if has_key else '❌ Not set'}")
    elif provider == 'ollama':
        print_colored("\nOllama Settings:", Colors.YELLOW)
        print(f"  BASE_URL: {env_vars.get('OLLAMA_BASE_URL', 'http://localhost:11434')}")
        print(f"  MODEL: {env_vars.get('OLLAMA_MODEL', 'qwen2.5:7b')}")
    elif provider == 'none':
        print_colored("\n⚠️ No LLM provider configured. Using template-based generation.", Colors.YELLOW)
    
    print_colored("="*60 + "\n", Colors.RESET)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Switch LLM provider linh hoạt',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Switch to local model
  python switch_llm_provider.py local
  
  # Switch to local with custom model
  python switch_llm_provider.py local --model Qwen/Qwen2.5-14B-Instruct --device cuda --8bit
  
  # Switch to API mode
  python switch_llm_provider.py api
  
  # Switch to API with custom URL
  python switch_llm_provider.py api --url https://custom-api.hf.space/api
  
  # Switch to OpenAI
  python switch_llm_provider.py openai
  
  # Switch to Anthropic
  python switch_llm_provider.py anthropic
  
  # Switch to Ollama
  python switch_llm_provider.py ollama
  
  # Disable LLM (use templates only)
  python switch_llm_provider.py none
  
  # Show current configuration
  python switch_llm_provider.py show
        """
    )
    
    parser.add_argument(
        'provider',
        choices=['local', 'api', 'openai', 'anthropic', 'ollama', 'none', 'show'],
        help='LLM provider to use'
    )
    
    # Local model options
    parser.add_argument('--model', '--model-path', dest='model_path',
                       help='Model path for local provider (e.g., Qwen/Qwen2.5-7B-Instruct)')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'],
                       help='Device for local model (auto, cpu, cuda)')
    parser.add_argument('--8bit', action='store_true',
                       help='Use 8-bit quantization for local model')
    parser.add_argument('--4bit', action='store_true',
                       help='Use 4-bit quantization for local model')
    
    # API mode options
    parser.add_argument('--url', '--api-url', dest='api_url',
                       help='API URL for API mode')
    
    args = parser.parse_args()
    
    if args.provider == 'show':
        show_current()
        return 0
    
    # Prepare kwargs
    kwargs = {}
    
    if args.provider == 'local':
        if args.model_path:
            kwargs['model_path'] = args.model_path
        if args.device:
            kwargs['device'] = args.device
        if args.__dict__.get('8bit'):
            kwargs['use_8bit'] = 'true'
            kwargs['use_4bit'] = 'false'
        elif args.__dict__.get('4bit'):
            kwargs['use_4bit'] = 'true'
            kwargs['use_8bit'] = 'false'
    elif args.provider == 'api':
        if args.api_url:
            kwargs['api_url'] = args.api_url
    
    # Set provider
    try:
        set_provider(args.provider, **kwargs)
        print_colored("\n💡 Tip: Restart your Django server để áp dụng thay đổi!", Colors.YELLOW)
        return 0
    except Exception as e:
        print_colored(f"❌ Error: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

