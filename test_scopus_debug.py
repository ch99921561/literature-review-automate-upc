# -*- coding: utf-8 -*-
"""Debug script para verificar view=COMPLETE de Scopus."""
import os
from urllib.parse import quote
import requests

api_key = os.getenv('SCOPUS_API_KEY')
title = 'AI Governance in a Complex and Rapidly Changing Regulatory Landscape'
query = f'TITLE("{title}")'
url = f'https://api.elsevier.com/content/search/scopus?query={quote(query)}&count=1&view=COMPLETE'

print(f'API Key: {api_key[:10]}...')
print(f'URL: {url[:100]}...')

headers = {'X-ELS-APIKey': api_key}
r = requests.get(url, headers=headers)
print(f'Status: {r.status_code}')

if r.status_code == 200:
    data = r.json()
    entries = data.get('search-results', {}).get('entry', [])
    if entries:
        entry = entries[0]
        abstract = entry.get('dc:description', '') or entry.get('prism:description', '')
        print(f'Abstract: {abstract[:250] if abstract else "NO HAY"}...')
        print(f'Keys: {list(entry.keys())[:15]}')
else:
    print(f'Error: {r.text[:400]}')
