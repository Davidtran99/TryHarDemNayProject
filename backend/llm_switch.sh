#!/bin/bash
# Quick script để switch LLM provider
# Usage: ./llm_switch.sh [local|api|openai|anthropic|ollama|none]

PROVIDER=${1:-show}

case $PROVIDER in
    local)
        python3 switch_llm_provider.py local
        ;;
    api)
        python3 switch_llm_provider.py api
        ;;
    openai)
        python3 switch_llm_provider.py openai
        ;;
    anthropic)
        python3 switch_llm_provider.py anthropic
        ;;
    ollama)
        python3 switch_llm_provider.py ollama
        ;;
    none)
        python3 switch_llm_provider.py none
        ;;
    show|*)
        python3 switch_llm_provider.py show
        ;;
esac

