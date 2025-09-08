import json
import os
from typing import List, Set, Dict, Any
from datetime import datetime
import logging

LABELS_FILE = "labels.json"


class LabelManager:

    def __init__(self):
        self.labels_file = LABELS_FILE
        self._ensure_labels_file()
        self._check_and_fix_format()

    def _ensure_labels_file(self):
        if not os.path.exists(self.labels_file):
            default_data = {
                "labels": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }
            self._save_labels_data(default_data)

    def _check_and_fix_format(self):
        try:
            data = self._load_labels_data()

        except Exception as e:
            logging.error(f"Error checking labels file format: {e}")

            self._ensure_labels_file()

    def _load_labels_data(self) -> Dict[str, Any]:
        try:
            with open(self.labels_file, "r", encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, list):
                    logging.info("Detected old labels format, migrating to new format")
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
        return data.get("labels", [])

    def get_all_labels_safe(self) -> List[str]:
        try:
            return self.get_all_labels()
        except Exception as e:
            logging.error(f"Error getting labels, trying fallback: {e}")

            try:
                with open(self.labels_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    else:
                        return []
            except:
                return []

    def add_label(self, label: str) -> Dict[str, Any]:
        label = label.strip()
        if not label:
            return {"success": False, "message": "Label cannot be empty"}

        data = self._load_labels_data()
        labels = data.get("labels", [])

        if label in labels:
            return {"success": False, "message": f"Label '{label}' already exists"}

        labels.append(label)
        data["labels"] = labels
        self._save_labels_data(data)

        logging.info(f"Label '{label}' added successfully")
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

        logging.info(f"Label '{label}' removed successfully")
        return {"success": True, "message": f"Label '{label}' removed successfully"}

    def _clean_label_from_data(self, label: str):

        try:

            with open("servers.json", "r", encoding="utf-8") as f:
                servers = json.load(f)

            updated = False
            cleaned_count = 0

            for server_name, server_info in servers.items():
                if server_info.get("label") == label:
                    server_info["label"] = ""
                    updated = True
                    cleaned_count += 1

            if updated:
                with open("servers.json", "w", encoding="utf-8") as f:
                    json.dump(servers, f, indent=4, ensure_ascii=False)
                logging.info(f"Cleaned label '{label}' from {cleaned_count} servers")
        except Exception as e:
            logging.error(f"Error cleaning label from servers: {e}")

        try:

            with open("domains.json", "r", encoding="utf-8") as f:
                domains = json.load(f)

            updated = False
            cleaned_count = 0

            for domain_name, domain_info in domains.items():
                if domain_info.get("label") == label:
                    domain_info["label"] = ""
                    updated = True
                    cleaned_count += 1

            if updated:
                with open("domains.json", "w", encoding="utf-8") as f:
                    json.dump(domains, f, indent=4, ensure_ascii=False)
                logging.info(f"Cleaned label '{label}' from {cleaned_count} domains")
        except Exception as e:
            logging.error(f"Error cleaning label from domains: {e}")

        try:
            from label_sync import force_sync

            current_labels = self.get_all_labels()
            force_sync()
            logging.info(f"Force synced labels after cleaning '{label}'")
        except Exception as e:
            logging.error(f"Error force syncing after cleaning: {e}")

    def sync_labels_from_data(self) -> Dict[str, Any]:
        try:

            existing_labels = set(self.get_all_labels())

            data_labels = set()

            try:
                with open("servers.json", "r", encoding="utf-8") as f:
                    servers = json.load(f)

                for server_info in servers.values():
                    label = server_info.get("label", "").strip()
                    if label:
                        data_labels.add(label)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            try:
                with open("domains.json", "r", encoding="utf-8") as f:
                    domains = json.load(f)

                for domain_info in domains.values():
                    label = domain_info.get("label", "").strip()
                    if label:
                        data_labels.add(label)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            try:
                with open("labels.json", "r", encoding="utf-8") as f:
                    labels_data = json.load(f)
                    if isinstance(labels_data, list):
                        for label in labels_data:
                            if label and label.strip():
                                data_labels.add(label.strip())
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            new_labels = data_labels - existing_labels

            if new_labels:
                data = self._load_labels_data()
                labels = data.get("labels", [])

                for label in new_labels:
                    if label not in labels:
                        labels.append(label)

                data["labels"] = labels
                self._save_labels_data(data)

                logging.info(f"Synced {len(new_labels)} new labels: {list(new_labels)}")
                return {
                    "success": True,
                    "message": f"Synced {len(new_labels)} new labels from data",
                    "new_labels": list(new_labels),
                }
            else:
                return {"success": True, "message": "No new labels found to sync"}

        except Exception as e:
            logging.error(f"Error syncing labels: {e}")
            return {"success": False, "message": f"Error syncing labels: {str(e)}"}

    def get_labels_usage(self) -> Dict[str, Any]:
        try:
            labels = self.get_all_labels()
            usage = {label: {"servers": 0, "domains": 0} for label in labels}

            try:
                with open("servers.json", "r", encoding="utf-8") as f:
                    servers = json.load(f)

                for server_info in servers.values():
                    label = server_info.get("label", "").strip()
                    if label and label in usage:
                        usage[label]["servers"] += 1
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            try:
                with open("domains.json", "r", encoding="utf-8") as f:
                    domains = json.load(f)

                for domain_info in domains.values():
                    label = domain_info.get("label", "").strip()
                    if label and label in usage:
                        usage[label]["domains"] += 1
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            return {"success": True, "usage": usage}

        except Exception as e:
            logging.error(f"Error getting label usage: {e}")
            return {"success": False, "message": f"Error getting usage: {str(e)}"}

    def validate_label(self, label: str) -> Dict[str, Any]:
        label = label.strip()

        if not label:
            return {"valid": False, "message": "Label cannot be empty"}

        if len(label) > 50:
            return {
                "valid": False,
                "message": "Label cannot be longer than 50 characters",
            }

        invalid_chars = ["<", ">", '"', "'", "&", "`", "\\", "/", "|"]
        for char in invalid_chars:
            if char in label:
                return {"valid": False, "message": f"Label cannot contain '{char}'"}

        return {"valid": True, "message": "Label is valid"}

    def export_labels(self) -> Dict[str, Any]:
        try:
            data = self._load_labels_data()
            usage = self.get_labels_usage()

            export_data = {
                "labels": data.get("labels", []),
                "metadata": {
                    "created_at": data.get("created_at"),
                    "last_updated": data.get("last_updated"),
                    "version": data.get("version", "1.0"),
                    "total_labels": len(data.get("labels", [])),
                },
                "usage": usage.get("usage", {}) if usage.get("success") else {},
            }

            return {"success": True, "data": export_data}

        except Exception as e:
            logging.error(f"Error exporting labels: {e}")
            return {"success": False, "message": f"Error exporting: {str(e)}"}

    def auto_sync_after_operation(self) -> Dict[str, Any]:

        logging.info("Auto-sync disabled to prevent label conflicts")
        return {"success": True, "message": "Auto-sync disabled to prevent conflicts"}

    def force_sync_all(self) -> Dict[str, Any]:
        try:

            all_labels = set()

            current_labels = self.get_all_labels()
            all_labels.update(current_labels)

            try:
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    settings_labels = settings.get("labels", [])
                    all_labels.update(settings_labels)
            except Exception as e:
                logging.error(f"Error reading settings.json: {e}")

            try:
                with open("servers.json", "r", encoding="utf-8") as f:
                    servers = json.load(f)
                    for server_info in servers.values():
                        label = server_info.get("label", "").strip()
                        if label:
                            all_labels.add(label)
            except Exception as e:
                logging.error(f"Error reading servers.json: {e}")

            try:
                with open("domains.json", "r", encoding="utf-8") as f:
                    domains = json.load(f)
                    for domain_info in domains.values():
                        label = domain_info.get("label", "").strip()
                        if label:
                            all_labels.add(label)
            except Exception as e:
                logging.error(f"Error reading domains.json: {e}")

            final_labels = sorted(list(all_labels))

            self._save_labels_data(
                {
                    "labels": final_labels,
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                }
            )

            try:
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)

                settings["labels"] = final_labels
                settings["default_labels"] = final_labels

                with open("settings.json", "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.error(f"Error updating settings.json: {e}")

            logging.info(f"✅ Force sync completed: {len(final_labels)} labels synced")
            return {
                "success": True,
                "message": f"Force sync completed: {len(final_labels)} labels synced",
                "labels": final_labels,
            }

        except Exception as e:
            logging.error(f"Error in force sync: {e}")
            return {"success": False, "message": f"Force sync failed: {str(e)}"}


label_manager = LabelManager()


def get_all_labels() -> List[str]:
    return label_manager.get_all_labels_safe()


def add_label(label: str) -> Dict[str, Any]:
    return label_manager.add_label(label)


def remove_label(label: str) -> Dict[str, Any]:
    return label_manager.remove_label(label)


def sync_labels() -> Dict[str, Any]:
    return label_manager.sync_labels_from_data()


def auto_sync_labels_on_startup() -> Dict[str, Any]:
    try:
        result = label_manager.auto_sync_after_operation()
        if result.get("success"):
            logging.info("Auto-sync labels on startup completed successfully")
        return result
    except Exception as e:
        logging.error(f"Auto-sync labels on startup failed: {e}")
        return {"success": False, "message": f"Auto-sync failed: {str(e)}"}


def force_sync_all_labels() -> Dict[str, Any]:
    return label_manager.force_sync_all()


def auto_sync_after_operation() -> Dict[str, Any]:
    return label_manager.auto_sync_after_operation()
