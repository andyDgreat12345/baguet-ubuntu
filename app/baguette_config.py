"""Shared public-install identity settings; no personal account is compiled in."""
import json
import os
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
DEFAULTS = {'bot_id': 'baguette', 'owner_id': 'owner', 'owner_chat': 'Owner', 'group_chats': ['Example group'], 'vm_name': 'baguette', 'tart_binary': 'tart', 'proxy': 'direct', 'deepseek_model': 'deepseek-flash', 'vision_model': 'qwen3.5:9b', 'vision_base_url': 'http://127.0.0.1:11434/v1', 'embedding_base_url': 'http://127.0.0.1:11434', 'embedding_model': 'bge-m3'}
DEFAULTS.update(account_namespace='unbound', private_chats=[], deployment_mode='vm',
                persona_note='', group_participation='directed')

def runtime_path():
    return Path(os.environ.get('BAGUETTE_RUNTIME', str(BASE/'runtime'))).expanduser().resolve()

def load_config():
    path=Path(os.environ.get('BAGUETTE_CONFIG',str(runtime_path()/'installation.json')))
    value=dict(DEFAULTS)
    if path.exists():value.update(json.loads(path.read_text()))
    if value.get('deployment_mode')!='linux' and not value.get('private_chats'):
        value['private_chats']=[value['owner_chat']]
    if value.get('deployment_mode')!='linux' and value['account_namespace']=='unbound':
        value['account_namespace']=value['bot_id']  # Existing VM session IDs retain their scope.
    return value
