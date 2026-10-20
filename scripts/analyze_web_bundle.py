import re
import json
import os

bundle_path = r'C:\RE\axon_iot\web_extracted\BJnwUizG.js'
with open(bundle_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print(f"Bundle size: {len(content):,} characters")

# 1. Extract API URL paths
urls = list(set(re.findall(r'[\'"`](/api/[^\'"`\s\?]+|/dashboard/[^\'"`\s\?]+|/external/[^\'"`\s\?]+|/templates/[^\'"`\s\?]+)', content)))
urls.sort()
print(f"Extracted {len(urls)} API/dashboard paths")

# 2. Extract Web Widget Identifiers
widgets = list(set(re.findall(r'WEB_[A-Z0-9_]+', content)))
widgets.sort()
print(f"Web Widgets found ({len(widgets)}):")
for w in widgets:
    print(f"  {w}")

# 3. Extract Datastream and Data Types
types = list(set(re.findall(r'(INTEGER|DOUBLE|STRING|ENUM|LOCATION|VIRTUAL|DIGITAL|ANALOG)', content)))
print(f"Data Types found: {types}")

# 4. Extract Hardware Boards supported on web
boards = list(set(re.findall(r'(ESP32[A-Z0-9_\-]*|ESP8266[A-Z0-9_\-]*|Arduino[A-Z0-9_\-]*|Raspberry[A-Z0-9_\-]*)', content, re.IGNORECASE)))
print(f"Hardware profiles found: {len(boards)}")

# Save comprehensive findings
analysis = {
    'total_size_bytes': len(content),
    'urls': urls,
    'web_widgets': widgets,
    'data_types': types,
    'hardware_profiles': boards
}

out_file = r'C:\RE\axon_iot\web_extracted\bundle_analysis.json'
with open(out_file, 'w', encoding='utf-8') as out:
    json.dump(analysis, out, indent=2)

print(f"Analysis saved to {out_file}")
