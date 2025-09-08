import json
import os
import time
import threading
import logging
from typing import Dict, List, Any
from datetime import datetime
import asyncio


class AutoLabelSyncService:

    def __init__(self):
        self.labels_file = "labels.json"
        self.settings_file = "settings.json"
        self.servers_file = "servers.json"
        self.domains_file = "domains.json"
        self.running = False
        self.sync_thread = None
        self.last_sync = None
        self.sync_interval = 30
        self.file_watchers = {}

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - AutoLabelSync - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def start_service(self):
        if self.running:
            return

        self.running = True
        self.logger.info("🔄 Starting automatic label sync service...")

        self._perform_sync()

        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()

        self.logger.info("Automatic label sync service started")

    def stop_service(self):
        if not self.running:
            return

        self.running = False
        self.logger.info("🛑 Stopping automatic label sync service...")

        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)

        self.logger.info("Automatic label sync service stopped")

    def _sync_loop(self):
        while self.running:
            try:
                time.sleep(self.sync_interval)
                if self.running:
                    self._perform_sync()
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
                time.sleep(5)

    def _perform_sync(self):
        try:

            if self._files_changed():
                self.logger.info("Files changed, performing sync...")
                result = self._sync_all_labels()

                if result.get("success"):
                    self.logger.info(f"Sync completed: {result['message']}")
                    self.last_sync = datetime.now()
                else:
                    self.logger.warning(f"Sync warning: {result['message']}")

        except Exception as e:
            self.logger.error(f"Sync error: {e}")

    def _files_changed(self) -> bool:
        files_to_watch = [
            self.labels_file,
            self.settings_file,
            self.servers_file,
            self.domains_file,
        ]

        changed = False
        for file_path in files_to_watch:
            if os.path.exists(file_path):
                try:
                    mtime = os.path.getmtime(file_path)
                    if (
                        file_path not in self.file_watchers
                        or self.file_watchers[file_path] != mtime
                    ):
                        self.file_watchers[file_path] = mtime
                        changed = True
                except Exception:
                    pass

        return changed

    def _sync_all_labels(self) -> Dict[str, Any]:
        try:

            all_labels = set()

            web_labels = self._load_web_labels()
            all_labels.update(web_labels)

            bot_labels = self._load_bot_labels()
            all_labels.update(bot_labels)

            data_labels = self._load_data_labels()
            all_labels.update(data_labels)

            clean_labels = sorted(
                [label.strip() for label in all_labels if label and label.strip()]
            )

            self._update_labels_file(clean_labels)
            self._update_settings_file(clean_labels)

            cleaned_count = self._clean_orphaned_labels(clean_labels)

            return {
                "success": True,
                "message": f"Synced {len(clean_labels)} labels, cleaned {cleaned_count} orphaned",
                "labels": clean_labels,
                "cleaned_count": cleaned_count,
            }

        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def _load_web_labels(self) -> List[str]:
        try:
            if os.path.exists(self.labels_file):
                with open(self.labels_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [
                            label.strip() for label in data if label and label.strip()
                        ]
                    elif isinstance(data, dict) and "labels" in data:
                        return [
                            label.strip()
                            for label in data["labels"]
                            if label and label.strip()
                        ]
            return []
        except Exception:
            return []

    def _load_bot_labels(self) -> List[str]:
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    labels = data.get("labels", [])
                    return [
                        label.strip() for label in labels if label and label.strip()
                    ]
            return []
        except Exception:
            return []

    def _load_data_labels(self) -> List[str]:
        labels = set()

        try:
            if os.path.exists(self.servers_file):
                with open(self.servers_file, "r", encoding="utf-8") as f:
                    servers = json.load(f)
                    for server_info in servers.values():
                        label = server_info.get("label", "").strip()
                        if label:
                            labels.add(label)
        except Exception:
            pass

        try:
            if os.path.exists(self.domains_file):
                with open(self.domains_file, "r", encoding="utf-8") as f:
                    domains = json.load(f)
                    for domain_info in domains.values():
                        label = domain_info.get("label", "").strip()
                        if label:
                            labels.add(label)
        except Exception:
            pass

        return list(labels)

    def _update_labels_file(self, labels: List[str]):
        try:
            with open(self.labels_file, "w", encoding="utf-8") as f:
                json.dump(labels, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error updating labels.json: {e}")

    def _update_settings_file(self, labels: List[str]):
        try:

            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            else:
                settings = {}

            settings["labels"] = labels

            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error updating settings.json: {e}")

    def _clean_orphaned_labels(self, valid_labels: List[str]) -> int:
        cleaned_count = 0

        try:
            if os.path.exists(self.servers_file):
                with open(self.servers_file, "r", encoding="utf-8") as f:
                    servers = json.load(f)

                updated = False
                for server_name, server_info in servers.items():
                    label = server_info.get("label", "").strip()
                    if label and label not in valid_labels:
                        server_info["label"] = ""
                        updated = True
                        cleaned_count += 1
                        self.logger.info(
                            f"🧹 Cleaned orphaned label '{label}' from server '{server_name}'"
                        )

                if updated:
                    with open(self.servers_file, "w", encoding="utf-8") as f:
                        json.dump(servers, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error cleaning servers: {e}")

        try:
            if os.path.exists(self.domains_file):
                with open(self.domains_file, "r", encoding="utf-8") as f:
                    domains = json.load(f)

                updated = False
                for domain_name, domain_info in domains.items():
                    label = domain_info.get("label", "").strip()
                    if label and label not in valid_labels:
                        domain_info["label"] = ""
                        updated = True
                        cleaned_count += 1
                        self.logger.info(
                            f"🧹 Cleaned orphaned label '{label}' from domain '{domain_name}'"
                        )

                if updated:
                    with open(self.domains_file, "w", encoding="utf-8") as f:
                        json.dump(domains, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error cleaning domains: {e}")

        return cleaned_count

    def force_sync(self) -> Dict[str, Any]:
        self.logger.info("🔄 Force sync requested...")
        return self._sync_all_labels()

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "sync_interval": self.sync_interval,
            "files_watched": len(self.file_watchers),
        }


_auto_sync_service = None


def start_auto_sync_service():
    global _auto_sync_service
    if _auto_sync_service is None:
        _auto_sync_service = AutoLabelSyncService()
    _auto_sync_service.start_service()
    return _auto_sync_service


def stop_auto_sync_service():
    global _auto_sync_service
    if _auto_sync_service:
        _auto_sync_service.stop_service()


def get_auto_sync_service():
    return _auto_sync_service


def force_sync():
    global _auto_sync_service
    if _auto_sync_service:
        return _auto_sync_service.force_sync()
    return {"success": False, "message": "Service not running"}


def is_service_running():
    global _auto_sync_service
    return _auto_sync_service and _auto_sync_service.running


def _both_bot_and_panel_active() -> bool:
    try:
        import psutil
    except Exception:
        return False

    def proc_cmdline_contains(substrs):
        for p in psutil.process_iter(attrs=["cmdline"]):
            try:
                cmd = " ".join(p.info.get("cmdline") or [])
            except Exception:
                continue
            if any(s in cmd for s in substrs):
                return True
        return False

    bot_running = proc_cmdline_contains(
        [
            "watchguard_service_bot.py",
            "watchguard_launcher.py",
            "watchguard_bot.py",
        ]
    )
    panel_running = proc_cmdline_contains(
        [
            "watchguard_service_panel.py",
            "watchguard_web_dashboard.py",
        ]
    )
    return bot_running and panel_running


def auto_start_if_needed():
    if is_service_running():
        return
    try:
        if _both_bot_and_panel_active():
            start_auto_sync_service()
            print("🔄 Auto-sync service started (bot + panel detected)")
        else:

            pass
    except Exception as e:
        print(f"Could not start auto-sync service: {e}")


auto_start_if_needed()
