import re
import json

path = r'C:\RE\axon_iot\web_extracted\chunks\BKxBD2K5.js'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

print(f"Widget engine size: {len(code):,} characters")

# Find widget declarations / exports / types
# Common pattern in React bundle: {type:"...", name:"...", ...} or WEB_...
widget_types = list(set(re.findall(r'WEB_[A-Z0-9_]+', code)))
widget_types.sort()
print(f"Web Widgets in engine ({len(widget_types)}):")
for w in widget_types[:50]:
    print(f"  {w}")

# Find all virtual pin references
vpins = list(set(re.findall(r'V[0-9]{1,3}', code)))
print(f"\nVirtual Pins referenced: {len(vpins)} (e.g. {vpins[:10]})")

# Find widget property names
props = list(set(re.findall(r'(onLabel|offLabel|onColor|offColor|min|max|step|datastreams|pin|grid|width|height)', code)))
print(f"\nWidget Properties found: {props}")

# Save detailed widget catalog
catalog = {
    'file': 'BKxBD2K5.js',
    'size_chars': len(code),
    'widget_types': widget_types,
    'properties': props
}

with open(r'C:\RE\axon_iot\web_extracted\web_widget_catalog.json', 'w') as out:
    json.dump(catalog, out, indent=2)
print("Saved to web_widget_catalog.json")
