import json
import os
from typing import List, Dict, Any
from datetime import datetime


class SimpleLabelManager:

    def __init__(self):
        self.labels_file = "labels.json"
        self._ensure_labels_file()

    def _ensure_labels_file(self):
        if not os.path.exists(self.labels_file):
            default_data = {
                "labels": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }
            self._save_labels_data(default_data)

    def _load_labels_data(self) -> Dict[str, Any]:
        try:
            with open(self.labels_file, "r", encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, list):
                    new_data = {
                        "labels": data,
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "version": "1.0",
                    }
                    self._save_labels_data(new_data)
                    return new_data

                return data

        except (FileNotFoundError, json.JSONDecodeError):
            default_data = {
                "labels": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }
            self._save_labels_data(default_data)
            return default_data

    def _save_labels_data(self, data: Dict[str, Any]):
        data["last_updated"] = datetime.now().isoformat()
        with open(self.labels_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_all_labels(self) -> List[str]:
        data = self._load_labels_data()
        labels = data.get("labels", [])

        clean_labels = list(
            set([label.strip() for label in labels if label and label.strip()])
        )
        clean_labels.sort()
        return clean_labels

    def add_label(self, label: str) -> Dict[str, Any]:
        label = label.strip()
        if not label:
            return {"success": False, "message": "Label cannot be empty"}

        if len(label) > 50:
            return {
                "success": False,
                "message": "Label cannot be longer than 50 characters",
            }

        data = self._load_labels_data()
        labels = data.get("labels", [])

        if label in labels:
            return {"success": False, "message": f"Label '{label}' already exists"}

        labels.append(label)
        data["labels"] = labels
        self._save_labels_data(data)

        return {"success": True, "message": f"Label '{label}' added successfully"}

    def remove_label(self, label: str) -> Dict[str, Any]:
        label = label.strip()
        if not label:
            return {"success": False, "message": "Label cannot be empty"}

        data = self._load_labels_data()
        labels = data.get("labels", [])

        if label not in labels:
            return {"success": False, "message": f"Label '{label}' not found"}

        labels.remove(label)
        data["labels"] = labels
        self._save_labels_data(data)

        self._clean_label_from_data(label)

        return {"success": True, "message": f"Label '{label}' removed successfully"}

    def _clean_label_from_data(self, label: str):

        try:
            if os.path.exists("servers.json"):
                with open("servers.json", "r", encoding="utf-8") as f:
                    servers = json.load(f)

                updated = False
                for server_name, server_info in servers.items():
                    if server_info.get("label", "").strip() == label:
                        server_info["label"] = ""
                        updated = True

                if updated:
                    with open("servers.json", "w", encoding="utf-8") as f:
                        json.dump(servers, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error cleaning label from servers: {e}")

        try:
            if os.path.exists("domains.json"):
                with open("domains.json", "r", encoding="utf-8") as f:
                    domains = json.load(f)

                updated = False
                for domain_name, domain_info in domains.items():
                    if domain_info.get("label", "").strip() == label:
                        domain_info["label"] = ""
                        updated = True

                if updated:
                    with open("domains.json", "w", encoding="utf-8") as f:
                        json.dump(domains, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error cleaning label from domains: {e}")

    def update_dropdown_labels(self):

        return self.get_all_labels()


simple_label_manager = SimpleLabelManager()


def get_labels_for_dropdown() -> List[str]:
    return simple_label_manager.get_all_labels()


def add_new_label(label: str) -> Dict[str, Any]:
    return simple_label_manager.add_label(label)


def remove_existing_label(label: str) -> Dict[str, Any]:
    return simple_label_manager.remove_label(label)
