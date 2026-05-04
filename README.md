# django-system-resgistry

Reusable Django app for typed, registry-backed system settings.

## Features

- `SystemSetting` model with registry validation and typed accessors
- Host-defined setting registry loaded from Django settings or a provider callable
- Cache-aware service layer for runtime reads and writes
- Django admin with default reset and validation actions
- Sync management command to seed the database from the registry

## Installation

```bash
uv add django-system-resgistry
```

Add the app to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "system_resgistry",
]
```

Run migrations:

```bash
python manage.py migrate system_resgistry
```

## Define settings in the host app

This package provides the framework. Your project keeps its own setting definitions.

You can define them directly in Django settings:

```python
SYSTEM_RESGISTRY_DEFINITIONS = {
    ("api", "page_size"): {
        "type": int,
        "default": 20,
        "description": "Default API page size.",
        "min_value": 1,
        "max_value": 100,
    },
    ("features", "signup_enabled"): {
        "type": bool,
        "default": False,
        "description": "Allow self-service signup.",
    },
}
```

Or load them from a provider callable:

```python
SYSTEM_RESGISTRY_DEFINITIONS_PROVIDER = "config.system_settings.get_setting_definitions"
```

Provider callables must return the same mapping shape:

```python
def get_setting_definitions():
    return {
        ("billing", "trial_days"): {
            "type": int,
            "default": 14,
            "description": "Default paid trial length.",
            "min_value": 1,
        },
    }
```

If both are present, provider definitions are loaded first and `SYSTEM_RESGISTRY_DEFINITIONS`
overrides matching keys.

## Supported definition metadata

| Field | Purpose |
| --- | --- |
| `type` | Expected Python type or coercion callable |
| `default` | Default value used when no DB override exists |
| `description` | Human-readable admin/ops description |
| `choices` | Allowed values |
| `min_value` | Minimum numeric value |
| `max_value` | Maximum numeric value |
| `validator` | Optional callable for extra validation or normalization |

`dict` and `list` values are stored as JSON. Booleans accept `true/false`, `1/0`,
`yes/no`, and `on/off`.

## Reading and writing settings

Model-level access:

```python
from system_resgistry.models import SystemSetting

page_size = SystemSetting.get_value("api", "page_size", default=20)
SystemSetting.set_value("features", "signup_enabled", True)
```

Service-layer access with caching:

```python
from system_resgistry.services import SettingsService

page_size = SettingsService.get_setting("api", "page_size", default=20)
SettingsService.set_setting("features", "signup_enabled", True)
```

Convenience helpers:

```python
from system_resgistry.services import get_system_setting, set_system_setting

enabled = get_system_setting("features", "signup_enabled", default=False)
set_system_setting("features", "signup_enabled", True)
```

## Cache configuration

| Setting | Purpose | Default |
| --- | --- | --- |
| `SYSTEM_RESGISTRY_CACHE_PREFIX` | Cache key prefix | `system_resgistry:` |
| `SYSTEM_RESGISTRY_CACHE_TIMEOUT` | Cache TTL in seconds | `300` |

Cache entries are invalidated automatically when `SystemSetting` rows are saved or deleted.

## Management command

Seed or inspect the database-backed settings:

```bash
python manage.py sync_system_settings
python manage.py sync_system_settings --dry-run
python manage.py sync_system_settings --namespace api
python manage.py sync_system_settings --list-namespaces
python manage.py sync_system_settings --list-settings api
```

## Admin behavior

The admin surfaces the typed value, registered type, and registered default. It also includes:

- **Reset selected settings to registry defaults**
- **Validate selected settings against registry**

## Optional integration with django-editable-pages

`django-editable-pages` does not depend on this package, but you can point its resolver hooks
at `SystemSetting` or `SettingsService` from here:

```python
from system_resgistry.services import get_system_setting


def editable_pages_cache_timeout(*, scope: str, page_type: str | None, default: int) -> int:
    del page_type
    mapping = {
        "content_pages": ("cache", "content_pages_timeout_seconds"),
        "faqs": ("cache", "faq_timeout_seconds"),
    }
    namespace, key = mapping.get(scope, ("cache", "unused"))
    return int(get_system_setting(namespace, key, default=default))
```

## Development

```bash
cd django-system-resgistry
uv sync --extra dev
source .venv/bin/activate
pytest
ruff check system_resgistry tests
mypy system_resgistry tests
```
