import re
import json

path = r'C:\RE\axon_iot\web_extracted\chunks\C1__FT3m.js'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    code = f.read()

print(f"C1__FT3m size: {len(code):,} characters")

# Find template fields, tabs, routes
tabs = list(set(re.findall(r'["\'](datastreams|dashboard|metadata|events|lifecycle|converters|guides|automations)["\']', code, re.IGNORECASE)))
print(f"Template Tabs found: {tabs}")

# Find datastream types
ds_types = list(set(re.findall(r'["\'](INTEGER|DOUBLE|STRING|ENUM|LOCATION|DIGITAL|ANALOG)["\']', code)))
print(f"Datastream types found: {ds_types}")

# Find pin range
pins = list(set(re.findall(r'V[0-9]{1,3}', code)))
print(f"Virtual pins found: {len(pins)}")
