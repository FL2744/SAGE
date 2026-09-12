"""Shared model defaults and validation."""
import os

DEFAULT_MODEL = "gpt-5.6-luna"
MODEL_OPTIONS = (
    (DEFAULT_MODEL, "Luna — cost-sensitive workloads"),
    ("gpt-5.6-terra", "Terra — balance intelligence and cost"),
    ("gpt-5.6-sol", "Sol — complex professional work"),
    ("gpt-6-astra", "Astra — most capable"),
)


def validate_model(value):
    if not isinstance(value, str) or not value.strip() or any(c.isspace() for c in value.strip()):
        raise ValueError("Enter a model ID without spaces.")
    return value.strip()


def default_model():
    return validate_model(os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL)
