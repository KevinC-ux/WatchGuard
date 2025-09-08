import asyncio
from fastapi import FastAPI, Request, Form, HTTPException, Query, Depends, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from uvicorn import Config, Server
import os
import json
import secrets
from datetime import datetime
import pytz
from dateutil.parser import parse as parse_date
from data_manager import get_shared_data_manager, DataChangeEvent
from notification_service import setup_bot_notifications
from auth_service import auth_manager
from datetime import timezone

app = FastAPI(title="Renewal Management System")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:

        return RedirectResponse(url="/login", status_code=302)

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")


try:
    from version_util import APP_VERSION
except Exception:
    APP_VERSION = "v1.0.0"
if os.path.exists("templates"):
    try:
        templates.env.globals["APP_VERSION"] = APP_VERSION
    except Exception:
        pass


shared_dm = get_shared_data_manager()


@app.on_event("startup")
async def _init_bot_notifications():
    try:
        config_data = shared_dm.load_config()
        if config_data and config_data.get("TOKEN") and config_data.get("CHAT_IDS"):
            setup_bot_notifications(config_data["TOKEN"], config_data["CHAT_IDS"])
            try:
                print("✅ Bot notifications enabled")
            except Exception:
                pass
        else:
            try:
                print("[WARNING] Bot notifications disabled - No valid config found")
            except Exception:
                pass
    except Exception as e:
        try:
            print(f"[WARNING] Bot notifications setup failed: {e}")
        except Exception:
            pass


def get_current_user(session_id: str = Cookie(None)):
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = auth_manager.get_session_user(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")

    return username


def issue_csrf_token(response: JSONResponse = None) -> str:
    token = secrets.token_urlsafe(32)

    if response is not None:
        response.set_cookie(
            key="csrf_token", value=token, secure=False, httponly=False, samesite="lax"
        )
    return token


def cleanup_sessions():
    auth_manager.cleanup_expired_sessions()


def audit_log(event: str, ip: str, username: str = "-"):
    try:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"{ts}\t{ip}\t{username}\t{event}\n"
        with open("auth_audit.log", "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


class DataManager:
    @staticmethod
    def load_json_file(filename, default=None):
        if default is None:
            default = {}
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default

    @staticmethod
    def save_json_file(filename, data):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_servers():
        return DataManager.load_json_file("servers.json")

    @staticmethod
    def save_servers(servers):
        DataManager.save_json_file("servers.json", servers)

    @staticmethod
    def load_domains():
        return DataManager.load_json_file("domains.json")

    @staticmethod
    def save_domains(domains):
        DataManager.save_json_file("domains.json", domains)

    @staticmethod
    def load_settings():
        default_settings = {
            "warning_days": 5,
            "notification_hour": 9,
            "notification_minute": 0,
            "daily_notifications": True,
            "web_panel_enabled": False,
            "ssl_certfile": "",
            "ssl_keyfile": "",
        }
        return DataManager.load_json_file("settings.json", default_settings)

    @staticmethod
    def save_settings(settings):
        DataManager.save_json_file("settings.json", settings)


class StatusCalculator:
    @staticmethod
    def get_status(renewal_date_str, warning_days=5):
        try:
            tz = pytz.timezone("Asia/Tehran")
            now = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

            renew_dt = parse_date(renewal_date_str, dayfirst=False, yearfirst=True)
            if renew_dt.tzinfo is None:
                renew_dt = tz.localize(renew_dt)

            days_diff = (renew_dt.date() - now.date()).days

            if days_diff < 0:
                return "expired", days_diff
            elif days_diff <= warning_days:
                return "warning", days_diff
            else:
                return "safe", days_diff
        except:
            return "unknown", 0


class CostCalculator:
    @staticmethod
    def get_cost_summary():
        servers = DataManager.load_servers()
        domains = DataManager.load_domains()
        settings = DataManager.load_settings()

        server_usd = server_eur = domain_usd = domain_eur = 0.0

        for info in servers.values():
            status, _ = StatusCalculator.get_status(
                info["date"], settings.get("warning_days", 5)
            )

            if status == "expired":
                continue

            price_str = info.get("price", "0")
            if price_str.startswith("$"):
                try:
                    server_usd += float(price_str[1:])
                except:
                    pass
            elif price_str.startswith("€"):
                try:
                    server_eur += float(price_str[1:])
                except:
                    pass

        for info in domains.values():
            status, _ = StatusCalculator.get_status(
                info["date"], settings.get("warning_days", 5)
            )

            if status == "expired":
                continue

            price_str = info.get("price", "0")
            if price_str.startswith("$"):
                try:
                    domain_usd += float(price_str[1:])
                except:
                    pass
            elif price_str.startswith("€"):
                try:
                    domain_eur += float(price_str[1:])
                except:
                    pass

        total_usd = server_usd + domain_usd
        total_eur = server_eur + domain_eur

        lines = ["──────── 💰 Cost Summary ────────"]

        server_costs = []
        if server_usd > 0:
            server_costs.append(f"${server_usd:.2f}")
        if server_eur > 0:
            server_costs.append(f"€{server_eur:.2f}")
        lines.append(
            f"🖥️ Servers: {' + '.join(server_costs) if server_costs else '$0.00'}"
        )

        domain_costs = []
        if domain_usd > 0:
            domain_costs.append(f"${domain_usd:.2f}")
        if domain_eur > 0:
            domain_costs.append(f"€{domain_eur:.2f}")
        lines.append(
            f"🌐 Domains: {' + '.join(domain_costs) if domain_costs else '$0.00'}"
        )

        total_costs = []
        if total_usd > 0:
            total_costs.append(f"${total_usd:.2f}")
        if total_eur > 0:
            total_costs.append(f"€{total_eur:.2f}")

        if total_costs:
            lines.append(f"📊 Total: {' + '.join(total_costs)}")
        else:
            lines.append(f"📊 Total: $0.00")

        return "\n".join(lines)


class Validator:
    @staticmethod
    def is_valid_date(date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def is_future_date(date_str):
        try:
            renew_dt = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now().date()
            return renew_dt.date() >= today
        except ValueError:
            return False

    @staticmethod
    def is_valid_price(price_str):
        try:
            float(price_str)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_name(name):
        import re

        pattern = r"^[a-zA-Z0-9\-_\s\.]+$"
        return bool(re.match(pattern, name)) and len(name.strip()) > 0


class CurrencyHelper:
    @staticmethod
    def currency_symbol(code):
        return {"USD": "$", "EUR": "€"}.get(code, "")


class LabelHelper:
    @staticmethod
    def get_existing_labels():
        try:

            from label_service import simple_label_manager

            return simple_label_manager.get_all_labels()
        except Exception as e:
            print(f"Error loading labels with simple manager: {e}")

            try:
                if os.path.exists("labels.json"):
                    with open("labels.json", "r", encoding="utf-8") as f:
                        labels_data = json.load(f)
                        if isinstance(labels_data, dict) and "labels" in labels_data:
                            return sorted(
                                [
                                    label.strip()
                                    for label in labels_data["labels"]
                                    if label and label.strip()
                                ]
                            )
                        elif isinstance(labels_data, list):
                            return sorted(
                                [
                                    label.strip()
                                    for label in labels_data
                                    if label and label.strip()
                                ]
                            )
                return []
            except Exception as e2:
                print(f"Fallback error: {e2}")
                return []

    @staticmethod
    def add_label_to_settings(label):
        if not label or not label.strip():
            return

        label = label.strip()
        try:
            settings = DataManager.load_settings()

        except Exception as e:
            print(f"Error adding label to settings: {str(e)}")

    @staticmethod
    def sync_labels_with_settings():
        try:
            existing_labels = LabelHelper.get_existing_labels()
            settings = DataManager.load_settings()

            print(f"Synced {len(existing_labels)} labels with settings")

            try:
                if os.path.exists("labels.json"):
                    with open("labels.json", "r", encoding="utf-8") as f:
                        labels_data = json.load(f)

                    if isinstance(labels_data, dict) and "labels" in labels_data:

                        current_labels = labels_data["labels"]
                        updated = False

                        for label in existing_labels:
                            if label not in current_labels:
                                current_labels.append(label)
                                updated = True

                        if updated:
                            labels_data["labels"] = current_labels
                            labels_data["last_updated"] = datetime.now().isoformat()

                            with open("labels.json", "w", encoding="utf-8") as f:
                                json.dump(labels_data, f, indent=4, ensure_ascii=False)

                            print(
                                f"[SUCCESS] labels.json updated with {len(current_labels)} labels"
                            )
                    elif isinstance(labels_data, list):

                        new_labels_data = {
                            "labels": existing_labels,
                            "created_at": datetime.now().isoformat(),
                            "last_updated": datetime.now().isoformat(),
                            "version": "1.0",
                        }

                        with open("labels.json", "w", encoding="utf-8") as f:
                            json.dump(new_labels_data, f, indent=4, ensure_ascii=False)

                        print(
                            f"[SUCCESS] labels.json converted to new format with {len(existing_labels)} labels"
                        )

            except Exception as e:
                print(f"Error syncing with labels.json: {e}")

        except Exception as e:
            print(f"Error syncing labels with settings: {str(e)}")

    @staticmethod
    def remove_label_from_all_items(label):
        try:

            servers = DataManager.load_servers()
            servers_updated = False
            for name, info in servers.items():
                if info.get("label", "").strip() == label:
                    info["label"] = ""
                    servers_updated = True

            if servers_updated:
                DataManager.save_servers(servers)
                print(f"Removed label '{label}' from servers")

            domains = DataManager.load_domains()
            domains_updated = False
            for name, info in domains.items():
                if info.get("label", "").strip() == label:
                    info["label"] = ""
                    domains_updated = True

            if domains_updated:
                DataManager.save_domains(domains)
                print(f"Removed label '{label}' from domains")

        except Exception as e:
            print(f"Error removing label from items: {str(e)}")

    @staticmethod
    def get_labels_for_bot():
        try:
            settings = DataManager.load_settings()
            return settings.get("labels", [])
        except Exception as e:
            print(f"Error getting labels for bot: {str(e)}")
            return []


EMOJI_OPTIONS = [
    "🇺🇸",
    "🇬🇧",
    "🇩🇪",
    "🇫🇷",
    "🇨🇦",
    "🇦🇺",
    "🇮🇹",
    "🇪🇸",
    "🇳🇱",
    "🇸🇪",
    "🇷🇺",
    "🇨🇳",
    "🇯🇵",
    "🇰🇷",
    "🇧🇷",
    "🇮🇳",
    "🇹🇷",
    "🇫🇮",
    "🇳🇴",
    "🇩🇰",
]


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):

    try:
        existing = request.cookies.get("session_id")
        if existing and auth_manager.get_session_user(existing):
            return RedirectResponse(url="/", status_code=302)
    except Exception:
        pass

    response = templates.TemplateResponse("login.html", {"request": request})
    try:
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            key="csrf_token", value=token, secure=False, httponly=False, samesite="lax"
        )
    except Exception:
        pass
    return response


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(None),
):

    client_ip = request.client.host

    if auth_manager.is_ip_locked(client_ip):
        audit_log("locked_out", client_ip, username)
        return JSONResponse({"status": "error", "message": "Invalid login"})

    client_csrf = request.cookies.get("csrf_token")
    if not client_csrf or not csrf_token or client_csrf != csrf_token:
        return JSONResponse({"status": "error", "message": "Invalid login"})

    if username == auth_manager.config["username"] and auth_manager.verify_password(
        password
    ):

        session_id = auth_manager.create_session(username, client_ip)
        auth_manager.record_successful_login(client_ip)

        response = JSONResponse({"status": "success", "message": "Login successful!"})
        audit_log("login_success", client_ip, username)

        response.set_cookie(
            key="session_id",
            value=session_id,
            secure=False,
            httponly=True,
            samesite="lax",
        )

        issue_csrf_token(response)

        return response
    else:

        auth_manager.record_failed_attempt(client_ip)
        audit_log("login_failed", client_ip, username)
        return JSONResponse({"status": "error", "message": "Invalid login"})


@app.post("/logout")
async def logout(session_id: str = Cookie(None)):
    if session_id:
        auth_manager.logout(session_id)

    response = JSONResponse(
        {"status": "success", "message": "Logged out successfully!"}
    )

    response.delete_cookie("session_id")
    return response


@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request, username: str = Depends(get_current_user)):

    cleanup_sessions()

    servers = DataManager.load_servers()
    domains = DataManager.load_domains()
    settings = DataManager.load_settings()

    server_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in servers.values():
        status, _ = StatusCalculator.get_status(
            info["date"], settings.get("warning_days", 5)
        )
        if status in server_status_counts:
            server_status_counts[status] += 1

    domain_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in domains.values():
        status, _ = StatusCalculator.get_status(
            info["date"], settings.get("warning_days", 5)
        )
        if status in domain_status_counts:
            domain_status_counts[status] += 1

    cost_summary_lines = CostCalculator.get_cost_summary().split("\n")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "username": username,
            "server_expired": server_status_counts["expired"],
            "server_warning": server_status_counts["warning"],
            "server_safe": server_status_counts["safe"],
            "domain_expired": domain_status_counts["expired"],
            "domain_warning": domain_status_counts["warning"],
            "domain_safe": domain_status_counts["safe"],
            "cost_summary": cost_summary_lines,
        },
    )


@app.get("/servers", response_class=HTMLResponse)
async def servers_page(
    request: Request,
    filter: str = Query(None),
    label: str = Query(None),
    username: str = Depends(get_current_user),
):
    servers = DataManager.load_servers()
    settings = DataManager.load_settings()

    server_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in servers.values():
        status, _ = StatusCalculator.get_status(
            info["date"], settings.get("warning_days", 5)
        )
        if status in server_status_counts:
            server_status_counts[status] += 1

    processed_servers = {"expired": [], "warning": [], "safe": []}
    if servers:
        for name, info in servers.items():
            status, days_diff = StatusCalculator.get_status(
                info["date"], settings.get("warning_days", 5)
            )

            if filter and status != filter:
                continue

            if label and info.get("label", "").strip() != label.strip():
                continue

            emoji = (info.get("emoji", "") or "").strip()

            if days_diff < 0:
                status_text = f"Expired ({abs(days_diff)} days ago)"
                status_class = "expired"
            elif days_diff == 0:
                status_text = "Expires today!"
                status_class = "expired"
            elif days_diff == 1:
                status_text = "Expires tomorrow"
                status_class = "warning"
            elif days_diff <= settings.get("warning_days", 5):
                status_text = f"{days_diff} days remaining"
                status_class = "warning"
            else:
                status_text = f"{days_diff} days remaining"
                status_class = "safe"

            server_data = {
                "name": name,
                "emoji": emoji,
                "date": info["date"],
                "status_text": status_text,
                "status_class": status_class,
                "price": info["price"],
                "datacenter": info["datacenter"],
                "label": info.get("label", ""),
                "days_diff": days_diff,
            }

            processed_servers[status_class].append(server_data)

        for group in processed_servers.values():
            group.sort(key=lambda x: x["days_diff"])

    server_total_cost = 0
    total_servers = 0
    for group in processed_servers.values():
        for server in group:

            if server["status_class"] == "expired":
                continue
            price_str = str(server["price"])
            price_num = float(price_str.replace("$", "").replace("€", ""))
            server_total_cost += price_num
            total_servers += 1

    cost_summary = CostCalculator.get_cost_summary().split("\n")

    existing_labels = LabelHelper.get_existing_labels()

    return templates.TemplateResponse(
        "servers.html",
        {
            "request": request,
            "servers": processed_servers,
            "cost_summary": cost_summary,
            "server_expired": server_status_counts["expired"],
            "server_warning": server_status_counts["warning"],
            "server_safe": server_status_counts["safe"],
            "current_filter": filter,
            "current_label": label,
            "server_total_cost": server_total_cost,
            "total_servers": total_servers,
            "existing_labels": existing_labels,
        },
    )


@app.get("/domains", response_class=HTMLResponse)
async def domains_page(
    request: Request,
    filter: str = Query(None),
    label: str = Query(None),
    username: str = Depends(get_current_user),
):
    domains = DataManager.load_domains()
    settings = DataManager.load_settings()

    domain_status_counts = {"expired": 0, "warning": 0, "safe": 0}
    for info in domains.values():
        status, _ = StatusCalculator.get_status(
            info["date"], settings.get("warning_days", 5)
        )
        if status in domain_status_counts:
            domain_status_counts[status] += 1

    processed_domains = {"expired": [], "warning": [], "safe": []}
    if domains:
        for name, info in domains.items():
            status, days_diff = StatusCalculator.get_status(
                info["date"], settings.get("warning_days", 5)
            )

            if filter and status != filter:
                continue

            if label and info.get("label", "").strip() != label.strip():
                continue

            if days_diff < 0:
                status_text = f"Expired ({abs(days_diff)} days ago)"
                status_class = "expired"
            elif days_diff == 0:
                status_text = "Expires today!"
                status_class = "expired"
            elif days_diff == 1:
                status_text = "Expires tomorrow"
                status_class = "warning"
            elif days_diff <= settings.get("warning_days", 5):
                status_text = f"{days_diff} days remaining"
                status_class = "warning"
            else:
                status_text = f"{days_diff} days remaining"
                status_class = "safe"

            domain_data = {
                "name": name,
                "date": info["date"],
                "status_text": status_text,
                "status_class": status_class,
                "price": info["price"],
                "registrar": info["registrar"],
                "label": info.get("label", ""),
                "days_diff": days_diff,
            }

            processed_domains[status_class].append(domain_data)

        for group in processed_domains.values():
            group.sort(key=lambda x: x["days_diff"])

    domain_total_cost = 0
    total_domains = 0
    for group in processed_domains.values():
        for domain in group:

            if domain["status_class"] == "expired":
                continue
            price_str = str(domain["price"])
            price_num = float(price_str.replace("$", "").replace("€", ""))
            domain_total_cost += price_num
            total_domains += 1

    cost_summary = CostCalculator.get_cost_summary().split("\n")

    existing_labels = LabelHelper.get_existing_labels()

    return templates.TemplateResponse(
        "domains.html",
        {
            "request": request,
            "domains": processed_domains,
            "cost_summary": cost_summary,
            "domain_expired": domain_status_counts["expired"],
            "domain_warning": domain_status_counts["warning"],
            "domain_safe": domain_status_counts["safe"],
            "current_filter": filter,
            "current_label": label,
            "domain_total_cost": domain_total_cost,
            "total_domains": total_domains,
            "existing_labels": existing_labels,
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, username: str = Depends(get_current_user)):
    try:
        settings = DataManager.load_settings()
    except Exception as e:
        settings = {
            "warning_days": 5,
            "notification_hour": 9,
            "notification_minute": 0,
            "daily_notifications": True,
            "web_panel_enabled": False,
        }
        print(f"Error loading settings: {str(e)}")

    existing_labels = LabelHelper.get_existing_labels()

    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "settings": settings, "existing_labels": existing_labels},
    )


@app.get("/api/labels")
async def get_labels_api(username: str = Depends(get_current_user)):
    try:

        settings = DataManager.load_settings()
        settings_labels = settings.get("labels", [])

        existing_labels = LabelHelper.get_existing_labels()

        return JSONResponse(
            {
                "status": "success",
                "settings_labels": settings_labels,
                "existing_labels": existing_labels,
                "settings": settings,
            }
        )
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/api/labels/add")
async def add_label_api(
    label: str = Form(...), username: str = Depends(get_current_user)
):
    try:

        from label_service import simple_label_manager

        result = simple_label_manager.add_label(label)

        if result["success"]:

            try:
                from data_manager import get_shared_data_manager, DataChangeEvent

                dm = get_shared_data_manager()
                dm.notify_observers(
                    DataChangeEvent(
                        "add", "label", label.strip(), {"source": "webpanel"}
                    )
                )
            except Exception as _:
                pass
            return JSONResponse({"status": "success", "message": result["message"]})
        else:
            return JSONResponse({"status": "error", "message": result["message"]})

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.delete("/api/labels/remove")
async def remove_label_api(
    label: str = Form(...), username: str = Depends(get_current_user)
):
    try:

        from label_service import simple_label_manager

        result = simple_label_manager.remove_label(label)

        if result["success"]:

            try:
                from data_manager import get_shared_data_manager, DataChangeEvent

                dm = get_shared_data_manager()
                dm.notify_observers(
                    DataChangeEvent(
                        "delete", "label", label.strip(), {"source": "webpanel"}
                    )
                )
            except Exception as _:
                pass
            return JSONResponse({"status": "success", "message": result["message"]})
        else:
            return JSONResponse({"status": "error", "message": result["message"]})

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/api/labels/sync")
async def sync_labels_api(username: str = Depends(get_current_user)):
    try:

        LabelHelper.sync_labels_with_settings()

        try:
            from label_manager import label_manager

            sync_result = label_manager.auto_sync_after_operation()
            if sync_result.get("success"):
                print(f"[SUCCESS] Label manager sync: {sync_result['message']}")
            else:
                print(f"[WARNING] Label manager sync warning: {sync_result['message']}")
        except ImportError:
            print("Label manager not available, using web panel sync only")
        except Exception as e:
            print(f"Error with label manager sync: {e}")

        return JSONResponse(
            {
                "status": "success",
                "message": "Labels synced successfully from all sources",
            }
        )
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/save_settings")
async def save_settings_post(
    username: str = Depends(get_current_user),
    warning_days: int = Form(...),
    notification_hour: int = Form(...),
    notification_minute: int = Form(...),
    daily_notifications: str = Form("false"),
):
    try:
        settings = DataManager.load_settings()

        daily_notifications_bool = daily_notifications.lower() == "true"

        settings.update(
            {
                "warning_days": warning_days,
                "notification_hour": notification_hour,
                "notification_minute": notification_minute,
                "daily_notifications": daily_notifications_bool,
            }
        )
        DataManager.save_settings(settings)
        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/add_server", response_class=HTMLResponse)
async def add_server_page(request: Request, username: str = Depends(get_current_user)):

    existing_labels = LabelHelper.get_existing_labels()

    return templates.TemplateResponse(
        "add_server.html",
        {
            "request": request,
            "emojis": EMOJI_OPTIONS,
            "existing_labels": existing_labels,
        },
    )


@app.post("/add_server")
async def add_server_post(
    username: str = Depends(get_current_user),
    name: str = Form(...),
    date: str = Form(...),
    price: str = Form(...),
    currency: str = Form(...),
    emoji: str = Form(...),
    datacenter: str = Form(...),
    label: str = Form(""),
):
    try:
        if (
            not Validator.is_valid_name(name)
            or not Validator.is_valid_date(date)
            or not Validator.is_future_date(date)
            or not Validator.is_valid_price(price)
        ):
            return JSONResponse({"status": "error", "message": "Invalid input data"})

        servers = DataManager.load_servers()
        if name in servers:
            return JSONResponse(
                {"status": "error", "message": "Server name already exists"}
            )

        symbol = CurrencyHelper.currency_symbol(currency)
        price_with_symbol = f"{symbol}{price}" if currency in ("USD", "EUR") else price

        new_entry = {
            "date": date,
            "price": price_with_symbol,
            "currency": currency,
            "datacenter": datacenter,
            "emoji": (emoji.strip() if isinstance(emoji, str) else "") or "",
            "label": label or "",
        }

        shared_dm.add_server(name, new_entry)

        if label and label.strip():
            LabelHelper.add_label_to_settings(label)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/add_domain", response_class=HTMLResponse)
async def add_domain_page(request: Request, username: str = Depends(get_current_user)):

    existing_labels = LabelHelper.get_existing_labels()

    return templates.TemplateResponse(
        "add_domain.html", {"request": request, "existing_labels": existing_labels}
    )


@app.post("/add_domain")
async def add_domain_post(
    username: str = Depends(get_current_user),
    name: str = Form(...),
    date: str = Form(...),
    price: str = Form(...),
    currency: str = Form(...),
    registrar: str = Form(...),
    label: str = Form(""),
):
    try:
        if (
            not Validator.is_valid_name(name)
            or not Validator.is_valid_date(date)
            or not Validator.is_future_date(date)
            or not Validator.is_valid_price(price)
        ):
            return JSONResponse({"status": "error", "message": "Invalid input data"})

        domains = DataManager.load_domains()
        if name in domains:
            return JSONResponse(
                {"status": "error", "message": "Domain name already exists"}
            )

        symbol = CurrencyHelper.currency_symbol(currency)
        price_with_symbol = f"{symbol}{price}" if currency in ("USD", "EUR") else price

        new_entry = {
            "date": date,
            "price": price_with_symbol,
            "currency": currency,
            "registrar": registrar,
            "label": label or "",
        }

        shared_dm.add_domain(name, new_entry)

        if label and label.strip():
            LabelHelper.add_label_to_settings(label)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/servers/edit/{name}", response_class=HTMLResponse)
async def edit_server_page(
    request: Request, name: str, username: str = Depends(get_current_user)
):
    servers = DataManager.load_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail="Server not found")

    server = servers[name]

    existing_labels = LabelHelper.get_existing_labels()

    return templates.TemplateResponse(
        "edit_server.html",
        {
            "request": request,
            "server_name": name,
            "server": server,
            "emojis": EMOJI_OPTIONS,
            "existing_labels": existing_labels,
        },
    )


@app.post("/servers/edit")
async def edit_server_post(
    original_name: str = Form(...),
    name: str = Form(...),
    date: str = Form(...),
    price: str = Form(...),
    currency: str = Form(...),
    emoji: str = Form(...),
    datacenter: str = Form(...),
    label: str = Form(""),
):
    try:
        if (
            not Validator.is_valid_name(name)
            or not Validator.is_valid_date(date)
            or not Validator.is_future_date(date)
            or not Validator.is_valid_price(price)
        ):
            return JSONResponse({"status": "error", "message": "Invalid input data"})

        servers = DataManager.load_servers()
        if original_name not in servers:
            return JSONResponse({"status": "error", "message": "Server not found"})

        if name != original_name and name in servers:
            return JSONResponse(
                {"status": "error", "message": "Server name already exists"}
            )

        symbol = CurrencyHelper.currency_symbol(currency)
        price_with_symbol = f"{symbol}{price}" if currency in ("USD", "EUR") else price

        updated_entry = {
            "date": date,
            "price": price_with_symbol,
            "currency": currency,
            "datacenter": datacenter,
            "emoji": (emoji.strip() if isinstance(emoji, str) else "") or "",
            "label": label,
        }

        shared_dm.update_server(original_name, name, updated_entry)

        if label and label.strip():
            LabelHelper.add_label_to_settings(label)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/domains/edit/{name}", response_class=HTMLResponse)
async def edit_domain_page(
    request: Request, name: str, username: str = Depends(get_current_user)
):
    domains = DataManager.load_domains()
    if name not in domains:
        raise HTTPException(status_code=404, detail="Domain not found")

    domain = domains[name]

    existing_labels = LabelHelper.get_existing_labels()

    return templates.TemplateResponse(
        "edit_domain.html",
        {
            "request": request,
            "domain_name": name,
            "domain": domain,
            "existing_labels": existing_labels,
        },
    )


@app.post("/domains/edit")
async def edit_domain_post(
    original_name: str = Form(...),
    name: str = Form(...),
    date: str = Form(...),
    price: str = Form(...),
    currency: str = Form(...),
    registrar: str = Form(...),
    label: str = Form(""),
):
    try:
        if (
            not Validator.is_valid_name(name)
            or not Validator.is_valid_date(date)
            or not Validator.is_future_date(date)
            or not Validator.is_valid_price(price)
        ):
            return JSONResponse({"status": "error", "message": "Invalid input data"})

        domains = DataManager.load_domains()
        if original_name not in domains:
            return JSONResponse({"status": "error", "message": "Domain not found"})

        if name != original_name and name in domains:
            return JSONResponse(
                {"status": "error", "message": "Domain name already exists"}
            )

        symbol = CurrencyHelper.currency_symbol(currency)
        price_with_symbol = f"{symbol}{price}" if currency in ("USD", "EUR") else price

        updated_entry = {
            "date": date,
            "price": price_with_symbol,
            "currency": currency,
            "registrar": registrar,
            "label": label,
        }

        shared_dm.update_domain(original_name, name, updated_entry)

        if label and label.strip():
            LabelHelper.add_label_to_settings(label)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/delete_server")
async def delete_server_old(
    name: str = Query(...), username: str = Depends(get_current_user)
):
    try:
        servers = DataManager.load_servers()
        if name not in servers:
            return JSONResponse({"status": "error", "message": "Server not found"})

        del servers[name]
        DataManager.save_servers(servers)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/delete_domain")
async def delete_domain_old(
    name: str = Query(...), username: str = Depends(get_current_user)
):
    try:
        domains = DataManager.load_domains()
        if name not in domains:
            return JSONResponse({"status": "error", "message": "Domain not found"})

        del domains[name]
        DataManager.save_domains(domains)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/servers/delete/{name}")
async def delete_server_new(name: str, username: str = Depends(get_current_user)):
    try:
        servers = DataManager.load_servers()
        if name not in servers:
            return JSONResponse(
                {"status": "error", "message": "Server not found"}, status_code=404
            )

        shared_dm.delete_server(name)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/domains/delete/{name}")
async def delete_domain_new(name: str, username: str = Depends(get_current_user)):
    try:
        domains = DataManager.load_domains()
        if name not in domains:
            return JSONResponse(
                {"status": "error", "message": "Domain not found"}, status_code=404
            )

        shared_dm.delete_domain(name)

        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def setup_web():
    try:

        try:
            config_data = shared_dm.load_config()
            if config_data and config_data.get("TOKEN") and config_data.get("CHAT_IDS"):
                setup_bot_notifications(config_data["TOKEN"], config_data["CHAT_IDS"])
                print("✅ Bot notifications enabled")
            else:
                print("[WARNING] Bot notifications disabled - No valid config found")
        except Exception as e:
            print(f"[WARNING] Bot notifications setup failed: {e}")

        settings = DataManager.load_settings()
        ssl_cert = settings.get("ssl_certfile") or ""
        ssl_key = settings.get("ssl_keyfile") or ""
        ssl_kwargs = {}
        if ssl_cert and ssl_key:
            ssl_kwargs = {"ssl_certfile": ssl_cert, "ssl_keyfile": ssl_key}

        config = Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            loop="asyncio",
            log_level="info",
            **ssl_kwargs,
        )
        server = Server(config)
        if ssl_kwargs:
            print("🌐 Web panel starting on https://localhost:8000")
        else:
            print("🌐 Web panel starting on http://localhost:8000")
        await server.serve()
    except Exception as e:
        print(f"❌ Web server error: {e}")
        return False
    return True


if __name__ == "__main__":
    asyncio.run(setup_web())
