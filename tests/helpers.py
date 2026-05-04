from __future__ import annotations

from typing import Any


def normalize_plan_code(value: Any) -> str:
    text = str(value).strip().lower()
    if text not in {"starter", "pro"}:
        msg = "Plan code must be either 'starter' or 'pro'."
        raise ValueError(msg)
    return text


def get_test_definitions() -> dict[tuple[str, str], dict[str, Any]]:
    return {
        ("api", "page_size"): {
            "type": int,
            "default": 20,
            "description": "Default page size.",
            "min_value": 1,
            "max_value": 100,
        },
        ("billing", "trial_days"): {
            "type": int,
            "default": 14,
            "description": "Trial length in days.",
            "min_value": 1,
            "max_value": 30,
        },
        ("billing", "plan_code"): {
            "type": str,
            "default": "starter",
            "description": "Default plan code.",
            "choices": ("starter", "pro"),
            "validator": normalize_plan_code,
        },
        ("features", "signup_enabled"): {
            "type": bool,
            "default": False,
            "description": "Allow self-service signup.",
        },
        ("notifications", "channels"): {
            "type": list,
            "default": ["email"],
            "description": "Enabled delivery channels.",
        },
        ("ui", "theme_config"): {
            "type": dict,
            "default": {"default": "light"},
            "description": "Theme configuration.",
        },
    }
