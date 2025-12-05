#!/usr/bin/env python3
import os
from pathlib import Path
from huggingface_hub import HfApi, login

SPACE_ID = 'davidtran999/hue-portal-backend'
ngrok_host = '0.tcp.ap.ngrok.io'
ngrok_port = '14180'  # Updated from terminal output
database_url = f'postgres://hue:huepass123@{ngrok_host}:{ngrok_port}/hue_portal'

# Get token
cache_file = Path.home() / '.cache' / 'huggingface' / 'token'
hf_token = cache_file.read_text().strip() if cache_file.exists() else None

if not hf_token:
    print('❌ Chưa có HF token! Chạy: huggingface-cli login')
    exit(1)

print('🔐 Đang login...')
login(token=hf_token)
api = HfApi()

print('🗑️  Đang xóa DATABASE_URL cũ...')
try:
    api.delete_space_variable(repo_id=SPACE_ID, key='DATABASE_URL')
    print('  ✅ Deleted variable')
except: pass
try:
    api.delete_space_secret(repo_id=SPACE_ID, key='DATABASE_URL')
    print('  ✅ Deleted secret')
except: pass

print('📝 Đang set DATABASE_URL mới...')
api.add_space_secret(repo_id=SPACE_ID, key='DATABASE_URL', value=database_url)

print(f'\n✅ Đã set DATABASE_URL thành công!')
print(f'   postgres://hue:***@{ngrok_host}:{ngrok_port}/hue_portal')
print('\n🚀 Space sẽ tự động rebuild với database mới!')




from pathlib import Path
from huggingface_hub import HfApi, login

SPACE_ID = 'davidtran999/hue-portal-backend'
ngrok_host = '0.tcp.ap.ngrok.io'
ngrok_port = '14180'  # Updated from terminal output
database_url = f'postgres://hue:huepass123@{ngrok_host}:{ngrok_port}/hue_portal'

# Get token
cache_file = Path.home() / '.cache' / 'huggingface' / 'token'
hf_token = cache_file.read_text().strip() if cache_file.exists() else None

if not hf_token:
    print('❌ Chưa có HF token! Chạy: huggingface-cli login')
    exit(1)

print('🔐 Đang login...')
login(token=hf_token)
api = HfApi()

print('🗑️  Đang xóa DATABASE_URL cũ...')
try:
    api.delete_space_variable(repo_id=SPACE_ID, key='DATABASE_URL')
    print('  ✅ Deleted variable')
except: pass
try:
    api.delete_space_secret(repo_id=SPACE_ID, key='DATABASE_URL')
    print('  ✅ Deleted secret')
except: pass

print('📝 Đang set DATABASE_URL mới...')
api.add_space_secret(repo_id=SPACE_ID, key='DATABASE_URL', value=database_url)

print(f'\n✅ Đã set DATABASE_URL thành công!')
print(f'   postgres://hue:***@{ngrok_host}:{ngrok_port}/hue_portal')
print('\n🚀 Space sẽ tự động rebuild với database mới!')


