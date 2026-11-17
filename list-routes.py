#!/usr/bin/env python3
"""List all registered Flask routes."""
import sys
sys.path.insert(0, '.')

from app import create_app

app = create_app()

print("=" * 80)
print("Registered Flask Routes")
print("=" * 80)

routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        'endpoint': rule.endpoint,
        'method': ','.join(rule.methods - {'OPTIONS', 'HEAD'}),
        'path': str(rule)
    })

# Sort by path
routes.sort(key=lambda x: x['path'])

# Find sync route
print("\nSearching for 'sync' routes:")
print("-" * 80)
sync_found = False
for route in routes:
    if 'sync' in route['path'].lower():
        print(f"{route['method']:10} {route['path']:60} -> {route['endpoint']}")
        sync_found = True

if not sync_found:
    print("❌ No 'sync' routes found!")

print("\nSearching for 'custom-views' routes:")
print("-" * 80)
cv_found = False
for route in routes:
    if 'custom-views' in route['path'].lower():
        print(f"{route['method']:10} {route['path']:60} -> {route['endpoint']}")
        cv_found = True

if not cv_found:
    print("❌ No 'custom-views' routes found!")

print("\n" + "=" * 80)
print(f"Total routes: {len(routes)}")
print("=" * 80)
