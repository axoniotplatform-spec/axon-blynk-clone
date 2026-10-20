import re
import json

bundle_path = r'C:\RE\axon_iot\web_extracted\BJnwUizG.js'
with open(bundle_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Find all template strings with /api/ or /api/v1 or URL paths
api_endpoints = set()

# Pattern for /api/... or /external/... or /dashboard/...
matches = re.findall(r'[`"\'](/api/[^`"\']+|/api/v1/[^`"\']+|/external/[^`"\']+|/dashboard/api/[^`"\']+|/static/[^`"\']+)[\'"`]', content)
for m in matches:
    api_endpoints.add(m)

# Also find axios/fetch pattern: url:`...` or url:"..."
url_patterns = re.findall(r'url\s*:\s*[`"\']([^`"\']+)[\'"`]', content)
for u in url_patterns:
    if '/' in u:
        api_endpoints.add(u)

# Also template literal interpolations: `${...}`
interpolated = re.findall(r'[`](/[^`]+)[`]', content)
for ip in interpolated:
    if any(k in ip for k in ['api', 'org', 'device', 'product', 'template', 'user', 'webhook', 'token']):
        api_endpoints.add(ip)

sorted_eps = sorted(list(api_endpoints))
print(f"Total API endpoint patterns discovered: {len(sorted_eps)}")
for ep in sorted_eps[:50]:
    print(f"  {ep}")

with open(r'C:\RE\axon_iot\web_extracted\api_endpoints_complete.json', 'w', encoding='utf-8') as f_out:
    json.dump(sorted_eps, f_out, indent=2)
print("Saved to api_endpoints_complete.json")
