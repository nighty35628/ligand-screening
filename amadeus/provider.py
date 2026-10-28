"""DeepSeek transport. Credentials stay in the local process."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def settings():
    cfg = {}
    path = Path(__file__).resolve().parents[1] / '.env.local'
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                cfg[key.strip()] = value.strip().strip('\"').strip("'")
    for key in ('DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_MODEL'):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
    return cfg


def request(path, data):
    cfg = settings()
    key = cfg.get('DEEPSEEK_API_KEY')
    if not key:
        raise ValueError('请在 .env.local 填写 DEEPSEEK_API_KEY 后重试。')
    req = urllib.request.Request(cfg.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/') + path,
                                 data=json.dumps(data).encode(), headers={
                                     'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (408, 429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise ValueError(f'DeepSeek 返回 HTTP {exc.code}，请检查服务配置或稍后重试。') from None
        except (urllib.error.URLError, TimeoutError):
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise ValueError('DeepSeek 连接暂时中断，请重试；项目内容已保存。') from None


def chat(messages, tools=None):
    body = {'model': settings().get('DEEPSEEK_MODEL', 'deepseek-flash'), 'messages': messages,
            'thinking': {'type': 'disabled'}, 'max_tokens': 2400, 'temperature': 0.3}
    if tools:
        body['tools'] = tools
    return request('/chat/completions', body)['choices'][0]['message']


def search(query):
    return request('/v1/tools/search', {'query': query[:128], 'count': 5, 'need_content': True}).get('results', [])


def fetch(url):
    return request('/v1/tools/fetch', {'url': url})
