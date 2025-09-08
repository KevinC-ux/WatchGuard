import json
import os
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import threading
import time


class DataChangeEvent:
    def __init__(self, event_type: str, data_type: str, item_name: str, data: Dict):
        self.event_type = event_type
        self.data_type = data_type
        self.item_name = item_name
        self.data = data
        self.timestamp = datetime.now()


class SharedDataManager:

    def __init__(self):
        self.observers: List[Callable] = []
        self.lock = threading.Lock()
        self.files = {
            "servers": "servers.json",
            "domains": "domains.json",
            "settings": "settings.json",
            "config": "config.json",
        }

    def add_observer(self, observer: Callable):
        with self.lock:
            self.observers.append(observer)

    def remove_observer(self, observer: Callable):
        with self.lock:
            if observer in self.observers:
                self.observers.remove(observer)

    def notify_observers(self, event: DataChangeEvent):
        with self.lock:
            for observer in self.observers:
                try:
                    observer(event)
                except Exception as e:
                    logging.error(f"Error notifying observer: {e}")

    def load_json_file(self, filename: str, default=None) -> Dict:
        if default is None:
            default = {}
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            return default
        except Exception as e:
            logging.error(f"Error loading {filename}: {e}")
            return default

    def save_json_file(self, filename: str, data: Dict):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving {filename}: {e}")
            raise

    def load_servers(self) -> Dict:
        return self.load_json_file(self.files["servers"])

    def save_servers(self, servers: Dict):
        self.save_json_file(self.files["servers"], servers)

    def add_server(self, name: str, data: Dict):
        servers = self.load_servers()
        servers[name] = data
        self.save_servers(servers)

        event = DataChangeEvent("add", "server", name, data)
        self.notify_observers(event)

    def update_server(self, old_name: str, new_name: str, data: Dict):
        servers = self.load_servers()

        if old_name != new_name and old_name in servers:
            del servers[old_name]

        servers[new_name] = data
        self.save_servers(servers)

        event = DataChangeEvent("update", "server", new_name, data)
        self.notify_observers(event)

    def delete_server(self, name: str):
        servers = self.load_servers()
        if name in servers:
            del servers[name]
            self.save_servers(servers)

            event = DataChangeEvent("delete", "server", name, {})
            self.notify_observers(event)

    def load_domains(self) -> Dict:
        return self.load_json_file(self.files["domains"])

    def save_domains(self, domains: Dict):
        self.save_json_file(self.files["domains"], domains)

    def add_domain(self, name: str, data: Dict):
        domains = self.load_domains()
        domains[name] = data
        self.save_domains(domains)

        event = DataChangeEvent("add", "domain", name, data)
        self.notify_observers(event)

    def update_domain(self, old_name: str, new_name: str, data: Dict):
        domains = self.load_domains()

        if old_name != new_name and old_name in domains:
            del domains[old_name]

        domains[new_name] = data
        self.save_domains(domains)

        event = DataChangeEvent("update", "domain", new_name, data)
        self.notify_observers(event)

    def delete_domain(self, name: str):
        domains = self.load_domains()
        if name in domains:
            del domains[name]
            self.save_domains(domains)

            event = DataChangeEvent("delete", "domain", name, {})
            self.notify_observers(event)

    def load_settings(self) -> Dict:
        default_settings = {
            "warning_days": 5,
            "notification_hour": 9,
            "notification_minute": 0,
            "daily_notifications": True,
            "CHAT_IDS": [],
            "web_panel_enabled": False,
        }
        return self.load_json_file(self.files["settings"], default_settings)

    def save_settings(self, settings: Dict):
        self.save_json_file(self.files["settings"], settings)

        event = DataChangeEvent("update", "settings", "global", settings)
        self.notify_observers(event)

    def load_config(self) -> Dict:
        return self.load_json_file(self.files["config"])

    def save_config(self, config: Dict):
        self.save_json_file(self.files["config"], config)

        event = DataChangeEvent("update", "config", "global", config)
        self.notify_observers(event)


_shared_data_manager = None
_lock = threading.Lock()


def get_shared_data_manager() -> SharedDataManager:
    global _shared_data_manager

    if _shared_data_manager is None:
        with _lock:
            if _shared_data_manager is None:
                _shared_data_manager = SharedDataManager()

    return _shared_data_manager


data_manager = get_shared_data_manager()
