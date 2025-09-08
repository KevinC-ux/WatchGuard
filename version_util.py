import os
import json


def read_version(default: str = "v1.0.0") -> str:

    env_ver = os.getenv("WATCHGUARD_VERSION")
    if env_ver and isinstance(env_ver, str) and env_ver.strip():
        return env_ver.strip()

    settings_paths = [
        os.path.join(os.getcwd(), "settings.json"),
        os.path.join(os.path.dirname(__file__), "settings.json"),
    ]
    for path in settings_paths:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ver = data.get("version") if isinstance(data, dict) else None
                    if isinstance(ver, str) and ver.strip():
                        return ver.strip()
        except Exception:
            pass

    return default


APP_VERSION = read_version()
