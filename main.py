
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def load_config():
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = Path(f"config.{env_name}.yaml")

    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
        config.update(yaml_config)

    # Layer 3: separate .env file
    env_file = dotenv_values(".env")

    dotenv_mapping = {
        "APP_PORT": "port",
        "NUM_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }

    for env_key, key in dotenv_mapping.items():
        if env_file.get(env_key) is not None:
            config[key] = env_file[env_key]

    # Layer 4: OS environment variables
    os_mapping = {
        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }

    for env_key, key in os_mapping.items():
        if env_key in os.environ:
            config[key] = os.environ[env_key]

    return config


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )

    return str(value)


@app.get("/effective-config")
async def effective_config(request: Request):
    config = load_config()

    # Layer 5: query-string overrides
    for item in request.query_params.getlist("set"):
        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        if key in config:
            config[key] = value

    # Apply required data types
    config = {
        key: coerce(key, value)
        for key, value in config.items()
    }

    # Never expose the real API key
    config["api_key"] = "****"

    return config
