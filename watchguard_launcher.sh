manage_watchguard() {
    clear
    echo -e "${BOLD}${CYAN}Manage WatchGuard Services${NC}"
    echo ""
    while true; do
        clear
        echo -e "${BOLD}${CYAN}Manage WatchGuard Services${NC}"
        echo ""
        echo -e " ${LGREEN}[1]${NC} ${WHITE}Manage Telegram Bot${NC}"
        echo -e " ${YELLOW}[2]${NC} ${WHITE}Manage Web Panel${NC}"
        echo -e " ${PURPLE}[3]${NC} ${WHITE}Return to Main Menu${NC}"
        echo -ne "${CYAN}Choose [1-3]:${NC} "
        read -r msel
        if [[ ! "$msel" =~ ^[1-3]$ ]]; then
            echo -e "${RED}Invalid choice. Please enter 1, 2, or 3.${NC}"
            sleep 1
            clear
            continue
        fi
        case $msel in
            1)
                manage_bot_service ;;
            2)
                manage_panel_service ;;
            3)
                SKIP_WAIT=1; return ;;
        esac
    done
}

manage_bot_service() {
    clear
    echo -e "${BOLD}${WHITE}Manage Telegram Bot${NC}"
    echo ""
    local svc="watchguard-bot.service"
    local suite="watchguard.service"
    if ! is_bot_installed; then
        echo -e "${YELLOW}Bot is not installed or running.${NC}"
        echo -ne "${CYAN}Press Enter to continue...${NC} "
        read -r; SKIP_WAIT=1; clear; return
    fi
    while true; do
        echo -e " ${CYAN}[1]${NC} ${WHITE}Restart TelegramBot${NC}"
        echo -e " ${YELLOW}[2]${NC} ${WHITE}View service logs${NC}"
        echo -e " ${LGREEN}[3]${NC} ${WHITE}View service status${NC}"
        echo -e " ${PURPLE}[4]${NC} ${WHITE}Back${NC}"
        echo -ne "${CYAN}Choose [1-4]:${NC} "
        read -r a
        if [[ ! "$a" =~ ^[1-4]$ ]]; then echo -e "${RED}Invalid choice.${NC}"; sleep 1; clear; continue; fi
        case $a in
            1)
                if command -v systemctl >/dev/null 2>&1; then
                    if systemctl list-unit-files | grep -q "^${suite}"; then
                        run_with_spinner "Restarting suite" systemctl restart watchguard.service || true
                    elif systemctl list-unit-files | grep -q "^${svc}"; then
                        run_with_spinner "Restarting bot" systemctl restart watchguard-bot.service || true
                    else
                        echo -e "${YELLOW}No managed service found to restart.${NC}"
                    fi
                else
                    echo -e "${YELLOW}systemctl not available; cannot restart service.${NC}"
                fi ;;
            2)
                if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "^${suite}"; then
                    journalctl -u watchguard.service -n 100 --no-pager | sed 's/^/  /'
                elif command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "^${svc}"; then
                    journalctl -u watchguard-bot.service -n 100 --no-pager | sed 's/^/  /'
                elif [ -f /var/log/watchguard-bot.log ]; then
                    tail -n 100 /var/log/watchguard-bot.log | sed 's/^/  /'
                elif [ -f /tmp/watchguard_bot.log ]; then
                    tail -n 100 /tmp/watchguard_bot.log | sed 's/^/  /'
                elif [ -f /tmp/watchguard_suite.log ]; then
                    tail -n 100 /tmp/watchguard_suite.log | sed 's/^/  /'
                else
                    echo -e "${YELLOW}No log file found.${NC}"
                fi ;;
            3)
                if command -v systemctl >/dev/null 2>&1; then
                    if systemctl list-unit-files | grep -q "^${suite}"; then
                        systemctl status watchguard.service --no-pager | sed 's/^/  /'
                    elif systemctl list-unit-files | grep -q "^${svc}"; then
                        systemctl status watchguard-bot.service --no-pager | sed 's/^/  /'
                    else
                        echo -e "${YELLOW}No managed service found.${NC}"
                    fi
                else
                    pgrep -f "watchguard_service_suite.py|watchguard_bot.py" >/dev/null 2>&1 && echo -e "${GREEN}  Running (process detected)${NC}" || echo -e "${YELLOW}  Not running${NC}"
                fi ;;
            4)
                SKIP_WAIT=1; return ;;
        esac
        echo -ne "${CYAN}Press Enter to continue...${NC} "; read -r; clear
    done
}

manage_panel_service() {
    clear
    echo -e "${BOLD}${WHITE}Manage Web Panel${NC}"
    echo ""
    local svc="watchguard-panel.service"
    local suite="watchguard.service"
    if ! is_panel_installed; then
        echo -e "${YELLOW}Web Panel is not installed or running.${NC}"
        echo -ne "${CYAN}Press Enter to continue...${NC} "
        read -r; SKIP_WAIT=1; clear; return
    fi
    while true; do
        echo -e " ${CYAN}[1]${NC} ${WHITE}Restart WebPanel${NC}"
        echo -e " ${YELLOW}[2]${NC} ${WHITE}View service logs${NC}"
        echo -e " ${LGREEN}[3]${NC} ${WHITE}View service status${NC}"
        echo -e " ${PURPLE}[4]${NC} ${WHITE}Obtain/Update SSL Certificate (Let's Encrypt)${NC}"
        echo -e " ${PURPLE}[5]${NC} ${WHITE}Back${NC}"
        echo -ne "${CYAN}Choose [1-5]:${NC} "
        read -r a
        if [[ ! "$a" =~ ^[1-5]$ ]]; then echo -e "${RED}Invalid choice.${NC}"; sleep 1; clear; continue; fi
        case $a in
            1)
                if command -v systemctl >/dev/null 2>&1; then
                    if systemctl list-unit-files | grep -q "^${suite}"; then
                        run_with_spinner "Restarting suite" systemctl restart watchguard.service || true
                    elif systemctl list-unit-files | grep -q "^${svc}"; then
                        run_with_spinner "Restarting panel" systemctl restart watchguard-panel.service || true
                    else
                        echo -e "${YELLOW}No managed service found to restart.${NC}"
                    fi
                else
                    echo -e "${YELLOW}systemctl not available; cannot restart service.${NC}"
                fi ;;
            2)
                if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "^${suite}"; then
                    journalctl -u watchguard.service -n 100 --no-pager | sed 's/^/  /'
                elif command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q "^${svc}"; then
                    journalctl -u watchguard-panel.service -n 100 --no-pager | sed 's/^/  /'
                elif [ -f /var/log/watchguard-panel.log ]; then
                    tail -n 100 /var/log/watchguard-panel.log | sed 's/^/  /'
                elif [ -f /tmp/watchguard_panel.log ]; then
                    tail -n 100 /tmp/watchguard_panel.log | sed 's/^/  /'
                elif [ -f /tmp/watchguard_suite.log ]; then
                    tail -n 100 /tmp/watchguard_suite.log | sed 's/^/  /'
                else
                    echo -e "${YELLOW}No log file found.${NC}"
                fi ;;
            3)
                if command -v systemctl >/dev/null 2>&1; then
                    if systemctl list-unit-files | grep -q "^${suite}"; then
                        systemctl status watchguard.service --no-pager | sed 's/^/  /'
                    elif systemctl list-unit-files | grep -q "^${svc}"; then
                        systemctl status watchguard-panel.service --no-pager | sed 's/^/  /'
                    else
                        echo -e "${YELLOW}No managed service found.${NC}"
                    fi
                else
                    pgrep -f "watchguard_service_suite.py|watchguard_web_dashboard.py" >/dev/null 2>&1 && echo -e "${GREEN}  Running (process detected)${NC}" || echo -e "${YELLOW}  Not running${NC}"
                fi ;;
            4)
                echo ""
                while true; do
                    read -rp "Enter domain name (e.g., example.com): " PANEL_DOMAIN
                    [ -n "$PANEL_DOMAIN" ] && break
                    echo -e "${RED}Domain cannot be empty.${NC}"
                done
                while true; do
                    read -rp "Enter admin email for Let's Encrypt: " LE_EMAIL
                    [ -n "$LE_EMAIL" ] && break
                    echo -e "${RED}Email cannot be empty.${NC}"
                done

                    if command -v apt-get >/dev/null 2>&1; then
                        run_with_spinner "Installing certbot" bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y certbot >/dev/null 2>&1" || true
                    elif command -v dnf >/dev/null 2>&1; then
                        run_with_spinner "Installing certbot" bash -c "dnf install -y certbot >/dev/null 2>&1" || true
                    elif command -v yum >/dev/null 2>&1; then
                        run_with_spinner "Installing certbot" bash -c "yum install -y certbot >/dev/null 2>&1" || true
                    elif command -v pacman >/dev/null 2>&1; then
                        run_with_spinner "Installing certbot" bash -c "pacman -Sy --noconfirm certbot >/dev/null 2>&1" || true
                    fi

                    echo -e "${YELLOW}Certbot will bind to port 80 temporarily. Ensure it's free.${NC}"
                    if certbot certonly --standalone -d "$PANEL_DOMAIN" -m "$LE_EMAIL" --agree-tos --no-eff-email --non-interactive; then
                        CERT_DIR="/etc/letsencrypt/live/${PANEL_DOMAIN}"
                        CERT_FILE="${CERT_DIR}/fullchain.pem"
                        KEY_FILE="${CERT_DIR}/privkey.pem"
                        if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
                            python3 - << PYSSL
import json
try:
    with open('settings.json','r',encoding='utf-8') as f:
        data=json.load(f)
except Exception:
    data={}
data['ssl_certfile'] = r'${CERT_FILE}'
data['ssl_keyfile'] = r'${KEY_FILE}'
with open('settings.json','w',encoding='utf-8') as f:
    json.dump(data,f,indent=4)
PYSSL
                            echo -e "${GREEN}Certificates installed and saved to settings.json.${NC}"
                            if command -v systemctl >/dev/null 2>&1; then
                                systemctl restart watchguard-panel.service || true
                            fi
                            clear
                            local width=68
                            local URL="https://${PANEL_DOMAIN}:${PANEL_PORT}"
                            echo -e "${LGREEN}"
                            printf "┌%s┐\n" "$(printf '─%.0s' $(seq 1 $width))"
                            printf "│%-${width}s│\n" ""
                            printf "│%-${width}s│\n" "  To access the Web Panel, open the following URL:"
                            printf "│%-${width}s│\n" "  ${URL}"
                            printf "│%-${width}s│\n" ""
                            printf "└%s┘\n" "$(printf '─%.0s' $(seq 1 $width))"
                            echo -e "${NC}"
                            create_cli_launcher
                            echo -ne "${CYAN}Press Enter to return to main menu...${NC} "
                            read -r
                            SKIP_WAIT=1
                            return
                        fi
                    else
                        echo -e "${RED}Standalone failed (port 80 busy?).${NC}"
                        while true; do
                            read -rp "Try DNS-01 manual challenge instead? (y/n): " TRY_DNS
                            if [[ "$TRY_DNS" =~ ^[YyNn]$ ]]; then
                                break
                            fi
                            echo -e "${RED}Input must be 'y' or 'n'.${NC}"
                        done
                        if [[ "$TRY_DNS" =~ ^[Yy]$ ]]; then
                            if certbot -d "$PANEL_DOMAIN" --manual --preferred-challenges dns certonly -m "$LE_EMAIL" --agree-tos --no-eff-email --manual-public-ip-logging-ok; then
                                CERT_DIR="/etc/letsencrypt/live/${PANEL_DOMAIN}"
                                CERT_FILE="${CERT_DIR}/fullchain.pem"
                                KEY_FILE="${CERT_DIR}/privkey.pem"
                                if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
                                    python3 - << PYSSL2
import json
try:
    with open('settings.json','r',encoding='utf-8') as f:
        data=json.load(f)
except Exception:
    data={}
data['ssl_certfile'] = r'${CERT_FILE}'
data['ssl_keyfile'] = r'${KEY_FILE}'
with open('settings.json','w',encoding='utf-8') as f:
    json.dump(data,f,indent=4)
PYSSL2
                                    echo -e "${GREEN}Certificates installed and saved to settings.json.${NC}"
                                    if command -v systemctl >/dev/null 2>&1; then
                                        systemctl restart watchguard-panel.service || true
                                    else
                                        OLD_PORT=""
                                        for pid in $(pgrep -f "watchguard_service_panel.py|uvicorn.*watchguard_web_dashboard:app" 2>/dev/null); do
                                            if [ -r "/proc/$pid/environ" ]; then
                                                ENVSTR=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep '^WG_PANEL_PORT=' || true)
                                                if [ -n "$ENVSTR" ]; then
                                                    OLD_PORT="${ENVSTR#WG_PANEL_PORT=}"
                                                    break
                                                fi
                                            fi
                                        done
                                        [ -z "$OLD_PORT" ] && OLD_PORT=8000
                                        pkill -f "watchguard_service_panel.py" >/dev/null 2>&1 || true
                                        pkill -f "uvicorn.*watchguard_web_dashboard:app" >/dev/null 2>&1 || true
                                        WG_PANEL_PORT="$OLD_PORT" nohup python3 watchguard_service_panel.py >/tmp/watchguard_panel.log 2>&1 &
                                    fi
                                    clear
                                    local width=68
                                    local URL="https://${PANEL_DOMAIN}:${PANEL_PORT}"
                                    echo -e "${LGREEN}"
                                    printf "┌%s┐\n" "$(printf '─%.0s' $(seq 1 $width))"
                                    printf "│%-${width}s│\n" ""
                                    printf "│%-${width}s│\n" "  To access the Web Panel, open the following URL:"
                                    printf "│%-${width}s│\n" "  ${URL}"
                                    printf "│%-${width}s│\n" ""
                                    printf "└%s┘\n" "$(printf '─%.0s' $(seq 1 $width))"
                                    echo -e "${NC}"
                                    create_cli_launcher
                                    echo -ne "${CYAN}Press Enter to return to main menu...${NC} "
                                    read -r
                                    SKIP_WAIT=1
                                    return
                                fi
                            else
                                echo -e "${RED}DNS-01 flow failed or was cancelled.${NC}"
                            fi
                        fi
                    fi
                ;;
            5)
                SKIP_WAIT=1; return ;;
        esac
        echo -ne "${CYAN}Press Enter to continue...${NC} "; read -r; clear
    done
}

install_watchguard_bot_only() {
    if is_bot_installed; then
        echo -e "\n${RED}Bot already appears installed/running. Returning to menu.${NC}"
        sleep 2
        SKIP_WAIT=1
        show_install_options
        return
    fi
    clear
    echo -e "${CYAN}Installing prerequisites...${NC}"

    if command -v apt-get >/dev/null 2>&1; then
        run_with_spinner "Updating package index (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1" || true
        run_with_spinner "Installing Python build deps (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip build-essential python3-dev libffi-dev >/dev/null 2>&1" || true
    elif command -v dnf >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (dnf)" bash -c "dnf install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v yum >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (yum)" bash -c "yum install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v pacman >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (pacman)" bash -c "pacman -Sy --noconfirm python python-pip base-devel libffi >/dev/null 2>&1" || true
    fi

    if [ ! -d .venv ]; then
        run_with_spinner "Creating virtual environment (.venv)" python3 -m venv .venv || true
    fi
    if [ -f .venv/bin/activate ]; then . .venv/bin/activate; elif [ -f .venv/Scripts/activate ]; then . .venv/Scripts/activate; fi
    if command -v pip >/dev/null 2>&1; then
        run_with_spinner "Upgrading pip" bash -c "pip install --upgrade pip >/dev/null 2>&1" || true
        run_with_spinner "Installing Python dependencies" bash -c "pip install -r requirements.txt >/dev/null 2>&1" || true
    fi
    sleep 0.2
    clear

    while true; do
        clear
        echo -e "${BOLD}${WHITE}Bot Configuration${NC}"
        echo -ne "${CYAN}Enter your Telegram Bot Token:${NC} "
        read -r INSTALL_TOKEN
        if [[ ! "$INSTALL_TOKEN" =~ ^[0-9]{6,10}:[A-Za-z0-9_-]{20,}$ ]]; then
            echo -e "${RED}Token format looks invalid. Please provide a valid token.${NC}"
            show_reset_animation
            continue
        fi
        if command -v curl >/dev/null 2>&1; then
            echo -ne "${PURPLE}Validating token with Telegram${NC}"
            for i in 1 2 3; do echo -n "."; sleep 0.2; done
            echo ""
            if ! curl -s "https://api.telegram.org/bot${INSTALL_TOKEN}/getMe" | grep -q '"ok":true'; then
                echo -e "${RED}The token appears to be invalid or unreachable. Please provide a valid token.${NC}"
                show_reset_animation
                continue
            fi
        fi

        echo ""
        while true; do
            echo -ne "${CYAN}Enter Telegram Chat ID(s) (comma separated for multiple):${NC} "
            read -r INSTALL_CHAT_IDS
            if [ -z "$INSTALL_CHAT_IDS" ]; then
                echo -e "${RED}Chat ID(s) cannot be empty. Please enter at least one numeric ID.${NC}"
                continue
            fi
            OLDIFS="$IFS"; IFS=','
            valid_ids=1
            for raw in $INSTALL_CHAT_IDS; do
                id="${raw//[[:space:]]/}"
                if ! [[ "$id" =~ ^[0-9]+$ ]]; then
                    valid_ids=0; break
                fi
            done
            IFS="$OLDIFS"
            if [ $valid_ids -eq 0 ]; then
                echo -e "${RED}Invalid Chat ID(s). Only digits are allowed, separated by commas.${NC}"
                continue
            fi
            break
        done

        clear
        echo -e "You entered:"
        echo -e "  Token: ${YELLOW}${INSTALL_TOKEN}${NC}"
        echo -e "  Chat IDs: ${YELLOW}${INSTALL_CHAT_IDS}${NC}"
        echo ""
        read -rp "Confirm? (y/n): " CONFIRM
        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            echo ""
            clear
            break
        fi
    done

    if [ -f config.json ]; then
        python3 - "$INSTALL_TOKEN" "$INSTALL_CHAT_IDS" << 'PYCONF2'
import json, sys
path = 'config.json'
token = sys.argv[1]
chat_ids_raw = sys.argv[2]
ids = []
for part in chat_ids_raw.split(','):
    p = part.strip()
    if not p:
        continue
    try:
        ids.append(int(p))
    except Exception:
        ids.append(p)
data = {}
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    pass
data['TOKEN'] = token
data['CHAT_IDS'] = ids
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
PYCONF2
    fi

    cat > watchguard_service_bot.py << 'PYRUN'
import json, sys
from watchguard_bot import setup_bot

def ensure_config():
    try:
        with open('config.json','r',encoding='utf-8') as f:
            cfg=json.load(f)
        if not cfg.get('TOKEN') or not cfg.get('CHAT_IDS'):
            print('[ERROR] Missing TOKEN or CHAT_IDS in config.json')
            sys.exit(1)
    except Exception as e:
        print(f'[ERROR] Cannot read config.json: {e}')
        sys.exit(1)

if __name__=='__main__':
    ensure_config()
    setup_bot()
PYRUN
    chmod +x watchguard_service_bot.py

    if command -v systemctl >/dev/null 2>&1; then
        echo -e "${CYAN}Creating systemd service (watchguard-bot.service)...${NC}"
        svc_path="/etc/systemd/system/watchguard-bot.service"
        sudo bash -c "cat > $svc_path" << 'SVCCFG'
[Unit]
Description=WatchGuard Bot
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=__WG_DIR__
Environment=VIRTUAL_ENV=__WG_DIR__/.venv
Environment=PATH=__WG_DIR__/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=__WG_DIR__/.venv/bin/python __WG_DIR__/watchguard_service_bot.py
Restart=on-failure
RestartSec=2
StandardOutput=append:/var/log/watchguard-bot.log
StandardError=append:/var/log/watchguard-bot.log
User=root

[Install]
WantedBy=multi-user.target
SVCCFG
        sed -i "s#__WG_DIR__#$(pwd)#g" "$svc_path"
        run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        run_with_spinner "Enabling bot service" systemctl enable watchguard-bot.service || true
        run_with_spinner "Starting bot service" systemctl restart watchguard-bot.service || true
        if ! systemctl is-active --quiet watchguard-bot.service; then
            echo -e "${RED}Bot service failed to start. Showing last log lines:${NC}"
            journalctl -u watchguard-bot.service -n 20 --no-pager | sed 's/^/  /'
        fi
        echo -e "${GREEN}Bot service is up. You can now access your bot.${NC}"
        echo -e "${WHITE}Logs:${NC} /var/log/watchguard-bot.log"
    else
        echo -e "${YELLOW}systemd not available; starting bot in background.${NC}"
        PYTHONDONTWRITEBYTECODE=1 nohup python3 watchguard_service_bot.py >/tmp/watchguard_bot.log 2>&1 &
        echo -e "${WHITE}Bot log:${NC} /tmp/watchguard_bot.log"
    fi
    create_cli_launcher
}
#!/bin/bash

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
PURPLE=$'\033[0;35m'
CYAN=$'\033[0;36m'
WHITE=$'\033[1;37m'
LGREEN=$'\033[1;32m'
B_MUSTARD=$'\033[38;5;178m'
BOLD=$'\033[1m'
NC=$'\033[0m'

clear

export PYTHONDONTWRITEBYTECODE=1

flush_stdin() {
    while IFS= read -r -t 0.01 -n 1000 _; do :; done
}

run_with_spinner() {
    local msg="$1"; shift
    ( "$@" ) &
    local pid=$!
    local spin='|/-\\'
    local i=0
    echo -ne "${CYAN}${msg}${NC} "
    while kill -0 "$pid" 2>/dev/null; do
        i=$(( (i+1) % 4 ))
        printf "\r${CYAN}%s ${YELLOW}%s${NC}" "$msg" "${spin:$i:1}"
        sleep 0.2
    done
    wait "$pid"; local ec=$?
    if [ $ec -eq 0 ]; then
        echo -e "\r${GREEN}${msg} - done${NC}    "
    else
        echo -e "\r${RED}${msg} - failed (${ec})${NC}"
    fi
    return $ec
}

ask_yes_no() {
    local prompt="$1"
    local default_ans="$2"
    local suffix
    local ans
    if [ "$default_ans" = "Y" ] || [ "$default_ans" = "y" ]; then
        suffix="(y/n) [Y]: "
        default_ans="Y"
    else
        suffix="(y/n) [N]: "
        default_ans="N"
    fi
    while true; do
        echo -ne "${CYAN}${prompt}${NC} ${WHITE}${suffix}${NC}"
        read -r ans
        if [ -z "$ans" ]; then
            [ "$default_ans" = "Y" ] && return 0 || return 1
        fi
        case "${ans}" in
            Y|y) return 0 ;;
            N|n) return 1 ;;
            *) echo -e "${RED}Please answer with 'y' or 'n'.${NC}" ;;
        esac
    done
}

create_cli_launcher() {
    local bin_path="/usr/local/bin/watchguard"
    [ -d /usr/local/bin ] || bin_path="/usr/bin/watchguard"
    local script_name
    script_name="$(basename "$0")"
    if [ "$EUID" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
        echo "[WARN] Need root to install launcher. Please run this script with sudo/root."
        return 0
    fi
    if [ "$EUID" -ne 0 ]; then
        sudo bash -c "cat > $bin_path" << 'LAUNCH'
#!/usr/bin/env bash
set -e
PROJECT_DIR="__WG_DIR__"
SCRIPT_FILE="__WG_SCRIPT__"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "WatchGuard project directory not found: $PROJECT_DIR"
  exit 1
fi
cd "$PROJECT_DIR"
if [ "$EUID" -ne 0 ]; then
  exec sudo -E bash "./$SCRIPT_FILE"
else
  exec bash "./$SCRIPT_FILE"
fi
LAUNCH
        sudo sed -i "s#__WG_DIR__#$(pwd)#g" "$bin_path"
        sudo sed -i "s#__WG_SCRIPT__#${script_name}#g" "$bin_path"
        sudo chmod +x "$bin_path"
    else
        cat > "$bin_path" << 'LAUNCH'
#!/usr/bin/env bash
set -e
PROJECT_DIR="__WG_DIR__"
SCRIPT_FILE="__WG_SCRIPT__"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "WatchGuard project directory not found: $PROJECT_DIR"
  exit 1
fi
cd "$PROJECT_DIR"
exec bash "./$SCRIPT_FILE"
LAUNCH
        sed -i "s#__WG_DIR__#$(pwd)#g" "$bin_path"
        sed -i "s#__WG_SCRIPT__#${script_name}#g" "$bin_path"
        chmod +x "$bin_path"
    fi
    echo "Launcher installed: watchguard (run this command anytime to open the menu)"
}

is_bot_installed() {
    service_present=1
    process_present=1
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files --type=service --no-legend --no-pager 2>/dev/null | awk '{print $1}' | grep -q "^watchguard-bot\.service$"; then service_present=0; fi
        if systemctl list-unit-files --type=service --no-legend --no-pager 2>/dev/null | awk '{print $1}' | grep -q "^watchguard\.service$"; then service_present=0; fi
        if [ -f /etc/systemd/system/watchguard-bot.service ] || [ -f /etc/systemd/system/watchguard.service ]; then service_present=0; fi
    fi
    if ps -eo command 2>/dev/null | grep -E "watchguard_service_bot\.py|watchguard_service_suite\.py|watchguard_bot\.py" >/dev/null 2>&1; then process_present=0; fi
    if [ $service_present -ne 0 ] && [ $process_present -ne 0 ]; then
        return 1
    fi
    if [ -f config.json ]; then
        if python3 - << 'PYCHK' >/dev/null 2>&1
import json
try:
    with open('config.json','r',encoding='utf-8') as f:
        d=json.load(f)
    tok=(d.get('TOKEN') or '').strip()
    ids=d.get('CHAT_IDS') or []
    ok=bool(tok) and bool(ids)
except Exception:
    ok=False
print('OK' if ok else 'NO')
exit(0 if ok else 1)
PYCHK
        then
            return 0
        else
            return 1
        fi
    fi
    return 1
}

is_panel_installed() {
    if command -v systemctl >/dev/null 2>&1; then
        systemctl list-unit-files --type=service --no-legend --no-pager 2>/dev/null | awk '{print $1}' | grep -q "^watchguard-panel\.service$" && return 0
        systemctl list-unit-files --type=service --no-legend --no-pager 2>/dev/null | awk '{print $1}' | grep -q "^watchguard\.service$" && return 0
        [ -f /etc/systemd/system/watchguard-panel.service ] && return 0
        [ -f /etc/systemd/system/watchguard.service ] && return 0
    fi
    ps -eo command 2>/dev/null | grep -E "watchguard_service_panel\.py|watchguard_service_suite\.py|watchguard_web_dashboard\.py" >/dev/null 2>&1 && return 0
    return 1
}

is_suite_installed() {
    if command -v systemctl >/dev/null 2>&1; then
        systemctl list-unit-files --type=service --no-legend --no-pager 2>/dev/null | awk '{print $1}' | grep -q "^watchguard\.service$" && return 0
        [ -f /etc/systemd/system/watchguard.service ] && return 0
        [ -f /lib/systemd/system/watchguard.service ] && return 0
    fi
    ps -eo command 2>/dev/null | grep -E "watchguard_service_suite\.py" >/dev/null 2>&1 && return 0
    return 1
}

stop_and_remove_bot_service() {
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-units --type=service --all | grep -q watchguard-bot.service; then
            run_with_spinner "Stopping bot service" systemctl stop watchguard-bot.service || true
            run_with_spinner "Disabling bot service" systemctl disable watchguard-bot.service || true
        fi
        if [ -f /etc/systemd/system/watchguard-bot.service ]; then
            run_with_spinner "Removing bot service file" rm -f /etc/systemd/system/watchguard-bot.service || true
            run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        fi
    else
        pkill -f "watchguard_service_bot.py" >/dev/null 2>&1 || true
        pkill -f "watchguard_launcher.py" >/dev/null 2>&1 || true
        pkill -f "watchguard_bot.py" >/dev/null 2>&1 || true
    fi
    [ -f /var/log/watchguard-bot.log ] && run_with_spinner "Removing bot log" rm -f /var/log/watchguard-bot.log || true
    [ -f /tmp/watchguard_bot.log ] && run_with_spinner "Removing bot temp log" rm -f /tmp/watchguard_bot.log || true
}

stop_and_remove_panel_service() {
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-units --type=service --all | grep -q watchguard-panel.service; then
            run_with_spinner "Stopping panel service" systemctl stop watchguard-panel.service || true
            run_with_spinner "Disabling panel service" systemctl disable watchguard-panel.service || true
        fi
        if [ -f /etc/systemd/system/watchguard-panel.service ]; then
            run_with_spinner "Removing panel service file" rm -f /etc/systemd/system/watchguard-panel.service || true
            run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        fi
    else
        pkill -f "watchguard_service_panel.py" >/dev/null 2>&1 || true
        pkill -f "watchguard_web_dashboard.py" >/dev/null 2>&1 || true
    fi
    [ -f /var/log/watchguard-panel.log ] && run_with_spinner "Removing panel log" rm -f /var/log/watchguard-panel.log || true
    [ -f /tmp/watchguard_panel.log ] && run_with_spinner "Removing panel temp log" rm -f /tmp/watchguard_panel.log || true
}

stop_and_remove_suite_service() {
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-units --type=service --all | grep -q watchguard.service; then
            run_with_spinner "Stopping suite service" systemctl stop watchguard.service || true
            run_with_spinner "Disabling suite service" systemctl disable watchguard.service || true
        fi
        if [ -f /etc/systemd/system/watchguard.service ]; then
            run_with_spinner "Removing suite service file" rm -f /etc/systemd/system/watchguard.service || true
            run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        fi
    else
        pkill -f "watchguard_service_suite.py" >/dev/null 2>&1 || true
    fi
    [ -f /var/log/watchguard.log ] && run_with_spinner "Removing suite log" rm -f /var/log/watchguard.log || true
    [ -f /tmp/watchguard_suite.log ] && run_with_spinner "Removing suite temp log" rm -f /tmp/watchguard_suite.log || true
}

get_suite_port() {
    local port="8000"
    if [ -f /etc/systemd/system/watchguard.service ]; then
        local line
        line=$(grep -E '^Environment=WG_PANEL_PORT=' /etc/systemd/system/watchguard.service 2>/dev/null || true)
        if [ -n "$line" ]; then
            port=${line#Environment=WG_PANEL_PORT=}
            port=$(echo "$port" | tr -d '\r\n')
        fi
    fi
    echo "$port"
}

create_panel_service_quick() {
    local PANEL_PORT="$1"; [ -z "$PANEL_PORT" ] && PANEL_PORT=8000
    cat > watchguard_service_panel.py << 'PYPANEL'
import asyncio, os, json
from uvicorn import Config, Server
from watchguard_web_dashboard import app

async def main():
    port = int(os.environ.get('WG_PANEL_PORT','8000'))
    ssl_kwargs = {}
    try:
        with open('settings.json','r',encoding='utf-8') as f:
            s=json.load(f)
        cert=(s.get('ssl_certfile') or '').strip()
        key=(s.get('ssl_keyfile') or '').strip()
        if cert and key:
            ssl_kwargs={'ssl_certfile': cert, 'ssl_keyfile': key}
    except Exception:
        pass
    cfg = Config(app=app, host='0.0.0.0', port=port, loop='asyncio', log_level='info', **ssl_kwargs)
    srv = Server(cfg)
    scheme = 'https' if ssl_kwargs else 'http'
    print(f"Web panel starting on {scheme}:
    await srv.serve()

if __name__=='__main__':
    asyncio.run(main())
PYPANEL
    chmod +x watchguard_service_panel.py
    if command -v systemctl >/dev/null 2>&1; then
        local svc_path="/etc/systemd/system/watchguard-panel.service"
        sudo bash -c "cat > $svc_path" << 'SVCPANEL'
[Unit]
Description=WatchGuard Web Panel
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=__WG_DIR__
Environment=VIRTUAL_ENV=__WG_DIR__/.venv
Environment=PATH=__WG_DIR__/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=WG_PANEL_PORT=__WG_PORT__
ExecStart=__WG_DIR__/.venv/bin/python __WG_DIR__/watchguard_service_panel.py
Restart=on-failure
RestartSec=2
StandardOutput=append:/var/log/watchguard-panel.log
StandardError=append:/var/log/watchguard-panel.log
User=root

[Install]
WantedBy=multi-user.target
SVCPANEL
        sed -i "s#__WG_DIR__#$(pwd)#g" "$svc_path"
        sed -i "s#__WG_PORT__#${PANEL_PORT}#g" "$svc_path"
        run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        run_with_spinner "Enabling panel service" systemctl enable watchguard-panel.service || true
        run_with_spinner "Starting panel service" systemctl restart watchguard-panel.service || true
    else
        PYTHONDONTWRITEBYTECODE=1 WG_PANEL_PORT="$PANEL_PORT" nohup python3 watchguard_service_panel.py >/tmp/watchguard_panel.log 2>&1 &
    fi
}

create_bot_service_quick() {
    cat > watchguard_service_bot.py << 'PYRUN'
import json, sys
from watchguard_bot import setup_bot

def ensure_config():
    try:
        with open('config.json','r',encoding='utf-8') as f:
            cfg=json.load(f)
        if not cfg.get('TOKEN') or not cfg.get('CHAT_IDS'):
            print('[ERROR] Missing TOKEN or CHAT_IDS in config.json')
            sys.exit(1)
    except Exception as e:
        print(f'[ERROR] Cannot read config.json: {e}')
        sys.exit(1)

if __name__=='__main__':
    ensure_config()
    setup_bot()
PYRUN
    chmod +x watchguard_service_bot.py
    if command -v systemctl >/dev/null 2>&1; then
        local svc_path="/etc/systemd/system/watchguard-bot.service"
        sudo bash -c "cat > $svc_path" << 'SVCCFG'
[Unit]
Description=WatchGuard Bot
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=__WG_DIR__
Environment=VIRTUAL_ENV=__WG_DIR__/.venv
Environment=PATH=__WG_DIR__/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=__WG_DIR__/.venv/bin/python __WG_DIR__/watchguard_service_bot.py
Restart=on-failure
RestartSec=2
StandardOutput=append:/var/log/watchguard-bot.log
StandardError=append:/var/log/watchguard-bot.log
User=root

[Install]
WantedBy=multi-user.target
SVCCFG
        sed -i "s#__WG_DIR__#$(pwd)#g" "$svc_path"
        run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        run_with_spinner "Enabling bot service" systemctl enable watchguard-bot.service || true
        run_with_spinner "Starting bot service" systemctl restart watchguard-bot.service || true
    else
        PYTHONDONTWRITEBYTECODE=1 nohup python3 watchguard_service_bot.py >/tmp/watchguard_bot.log 2>&1 &
    fi
}

show_reset_animation() {
    local seconds=3
    local msg="Returning to menu"
    for ((i=seconds; i>0; i--)); do
        local dots=$(( (seconds - i) % 4 ))
        printf "\r${YELLOW}%s%s in %ds...${NC}" "$msg" "$(printf '%*s' "$dots" | tr ' ' '.')" "$i"
        sleep 1
    done
    echo ""
}
install_watchguard() {
    clear
    echo -e "${BOLD}${GREEN}Starting WatchGuard installation...${NC}"
    echo -ne "${GREEN}Preparing environment${NC}"
    for i in 1 2 3; do echo -n "."; sleep 0.3; done; echo ""

    if command -v apt-get >/dev/null 2>&1; then
        run_with_spinner "Updating package index (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1" || true
        run_with_spinner "Installing Python build deps (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip build-essential python3-dev libffi-dev >/dev/null 2>&1" || true
    elif command -v dnf >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (dnf)" bash -c "dnf install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v yum >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (yum)" bash -c "yum install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v pacman >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (pacman)" bash -c "pacman -Sy --noconfirm python python-pip base-devel libffi >/dev/null 2>&1" || true
    fi

    if [ ! -d .venv ]; then
        run_with_spinner "Creating virtual environment (.venv)" python3 -m venv .venv || true
    fi
    if [ -f .venv/bin/activate ]; then
        . .venv/bin/activate
    elif [ -f .venv/Scripts/activate ]; then
        . .venv/Scripts/activate
    fi

    if command -v pip >/dev/null 2>&1; then
        run_with_spinner "Upgrading pip" bash -c "pip install --upgrade pip >/dev/null 2>&1" || true
        run_with_spinner "Installing Python dependencies" bash -c "pip install -r requirements.txt >/dev/null 2>&1" || true
        run_with_spinner "Ensuring argon2-cffi installed" bash -c "pip install -q argon2-cffi >/dev/null 2>&1" || true
    else
        echo -e "${YELLOW}pip not found; skipping Python dependency install.${NC}"
    fi

    echo ""
    echo -e "${BOLD}Configuration${NC}"
    read -rp "Enter Telegram Bot Token: " INSTALL_TOKEN
    read -rp "Enter Telegram Chat ID (single ID, can add more later): " INSTALL_CHAT_ID

    if [ -f config.json ]; then
        echo -e "${CYAN}Writing config.json...${NC}"
        python3 - "$INSTALL_TOKEN" "$INSTALL_CHAT_ID" << 'PYCONF'
import json, sys
path = 'config.json'
token = sys.argv[1]
chat_id = sys.argv[2]
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    data = {}
data['TOKEN'] = token
try:
    cid = int(chat_id)
    data['CHAT_IDS'] = [cid]
except Exception:
    data['CHAT_IDS'] = [chat_id]
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
print('OK')
PYCONF
    fi

    echo -e "${GREEN}All packages have been installed successfully.${NC}"
    sleep 1
    clear
    create_cli_launcher
    post_install_menu
}

show_install_options() {
    clear
    echo -e "${BOLD}${WHITE}WatchGuard Installer${NC}"
    local bot_note=""
    local both_note=""
    if is_bot_installed; then bot_note=" ${LGREEN}(already installed)${NC}"; fi
    if is_bot_installed && is_panel_installed; then both_note=" ${LGREEN}(already installed)${NC}"; fi

    echo -e " ${GREEN}[1]${NC} Install Telegram Bot${bot_note}"
    echo -e " ${YELLOW}[2]${NC} Install Web Panel + Bot${both_note}"
    echo -e " ${RED}[3]${NC} Return to Main Menu"
    echo ""
    flush_stdin
    echo -ne "${CYAN}Choose what to install [1-3] (default 2):${NC} "
    read -r sel
    if [ -z "$sel" ]; then sel=2; fi
    if [[ ! "$sel" =~ ^[1-3]$ ]]; then
        echo -e "${YELLOW}Invalid choice. Defaulting to 2 (Both).${NC}"
        sel=2
    fi
    case $sel in
        1)
            if is_bot_installed; then
                echo -e "\n${RED}Bot already installed. Returning to menu.${NC}"
                sleep 2; SKIP_WAIT=1; show_install_options; return
            fi
            install_watchguard_bot_only ;;
        2)
            if is_bot_installed && is_panel_installed; then
                echo -e "\n${RED}Both Bot and Web Panel are already installed. Returning to menu.${NC}"
                sleep 2; SKIP_WAIT=1; show_install_options; return
            fi
            clear
            echo -e "\n${CYAN}Setting up unified service for ${YELLOW}Web Panel + Bot${NC}..."
            is_bot_installed && stop_and_remove_bot_service || true
            is_panel_installed && stop_and_remove_panel_service || true
            sleep 1
            install_watchguard_suite ;;
        3)
            SKIP_WAIT=1
            return ;;
    esac
}

post_install_menu() {
    echo -e "${BOLD}Select components to install:${NC}"
    local bot_note=""; local both_note=""
    if is_bot_installed; then bot_note=" ${LGREEN}(already installed)${NC}"; fi
    if is_bot_installed && is_panel_installed; then both_note=" ${LGREEN}(already installed)${NC}"; fi
    echo -e " ${GREEN}[1]${NC} Install Telegram Bot${bot_note}"
    echo -e " ${YELLOW}[2]${NC} Install Web Panel + Bot${both_note}"
    echo -e " ${WHITE}[3]${NC} Return to Main Menu"
    echo ""
    flush_stdin
    echo -ne "${CYAN}Choose [1-3] (default 2):${NC} "
    read -r comp
    if [ -z "$comp" ]; then comp=2; fi
    if [[ ! "$comp" =~ ^[1-3]$ ]]; then
        echo -e "${YELLOW}Invalid choice. Defaulting to 2 (Both).${NC}"
        comp=2
    fi
    case $comp in
        1)
            if is_bot_installed; then
                echo -e "\n${RED}Bot already installed. Returning to menu.${NC}"
                return
            fi
            install_bot_component ;;
        2)
            if is_bot_installed && is_panel_installed; then
                echo -e "\n${RED}Both Bot and Web Panel are already installed. Returning to menu.${NC}"
                sleep 2; SKIP_WAIT=1; post_install_menu; return
            fi
            install_suite_component ;;
        3)
            SKIP_WAIT=1
            return ;;
    esac
}

install_bot_component() {
    echo -e "${GREEN}Starting WatchGuard Bot...${NC}"
    if command -v nohup >/dev/null 2>&1; then
        PYTHONDONTWRITEBYTECODE=1 nohup python3 watchguard_launcher.py >/tmp/watchguard_bot.log 2>&1 &
        echo -e "${WHITE}Bot log:${NC} /tmp/watchguard_bot.log"
    else
        PYTHONDONTWRITEBYTECODE=1 python3 watchguard_launcher.py &
    fi
}

install_panel_component() {
    echo -e "${CYAN}Starting WatchGuard Panel...${NC}"
    if command -v nohup >/dev/null 2>&1; then
        PYTHONDONTWRITEBYTECODE=1 nohup python3 watchguard_web_dashboard.py >/tmp/watchguard_panel.log 2>&1 &
        echo -e "${WHITE}Panel log:${NC} /tmp/watchguard_panel.log"
    else
        PYTHONDONTWRITEBYTECODE=1 python3 watchguard_web_dashboard.py &
    fi
    create_cli_launcher
}

install_suite_component() {
    echo -e "${CYAN}Starting WatchGuard (Web Panel + Bot)...${NC}"
    if command -v nohup >/dev/null 2>&1; then
        nohup python3 watchguard_service_suite.py >/tmp/watchguard_suite.log 2>&1 &
        echo -e "${WHITE}Suite log:${NC} /tmp/watchguard_suite.log"
    else
        python3 watchguard_service_suite.py &
    fi
    create_cli_launcher
}

install_watchguard_panel_only() {
    if is_panel_installed; then
        echo -e "\n${RED}Web Panel already appears installed/running. Returning to menu.${NC}"
        sleep 2
        SKIP_WAIT=1
        show_install_options
        return
    fi
    clear
    echo -e "${BOLD}${CYAN}Installing WatchGuard Web Panel...${NC}"

    if command -v apt-get >/dev/null 2>&1; then
        run_with_spinner "Updating package index (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1" || true
        run_with_spinner "Installing Python build deps (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip build-essential python3-dev libffi-dev >/dev/null 2>&1" || true
    elif command -v dnf >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (dnf)" bash -c "dnf install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v yum >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (yum)" bash -c "yum install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v pacman >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (pacman)" bash -c "pacman -Sy --noconfirm python python-pip base-devel libffi >/dev/null 2>&1" || true
    fi

    if [ ! -d .venv ]; then
        run_with_spinner "Creating virtual environment (.venv)" python3 -m venv .venv || true
    fi
    if [ -f .venv/bin/activate ]; then . .venv/bin/activate; elif [ -f .venv/Scripts/activate ]; then . .venv/Scripts/activate; fi
    if command -v pip >/dev/null 2>&1; then
        run_with_spinner "Upgrading pip" bash -c "pip install --upgrade pip >/dev/null 2>&1" || true
        run_with_spinner "Installing Python dependencies" bash -c "pip install -r requirements.txt >/dev/null 2>&1" || true
        run_with_spinner "Ensuring argon2-cffi installed" bash -c "pip install -q argon2-cffi >/dev/null 2>&1" || true
    fi

    if command -v tput >/dev/null 2>&1; then tput reset; else clear; fi
    echo ""
    while true; do
        echo -ne "${CYAN}Enter port for web panel (default 8000):${NC} "
        read -r PANEL_PORT
        if [ -z "$PANEL_PORT" ]; then PANEL_PORT=8000; fi
        if ! [[ "$PANEL_PORT" =~ ^[0-9]+$ ]] || [ "$PANEL_PORT" -lt 1 ] || [ "$PANEL_PORT" -gt 65535 ]; then
            echo -e "${RED}Invalid port. Please enter a number between 1 and 65535.${NC}"
            continue
        fi
        if command -v ss >/dev/null 2>&1; then
            if ss -ltnp 2>/dev/null | awk '{print $4" "$6}' | grep -E ":${PANEL_PORT}( |$)" >/dev/null 2>&1; then
                echo -e "${RED}This port is currently in use by another process. Please choose another port.${NC}"
                continue
            fi
        elif command -v lsof >/dev/null 2>&1; then
            if lsof -i TCP:"${PANEL_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
                echo -e "${RED}This port is currently in use by another process. Please choose another port.${NC}"
                continue
            fi
        fi
        if python3 - "$PANEL_PORT" << 'PYPORT'
import sys, socket
try:
    p = int(sys.argv[1])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", p))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PYPORT
        then
            echo -e "${GREEN}Panel port set to:${NC} ${YELLOW}$PANEL_PORT${NC}\n"
            break
        else
            echo -e "${RED}This port is already in use. Please choose another port.${NC}"
        fi
    done

    while true; do
        echo -ne "${CYAN}Enter admin username:${NC} "
        read -r PANEL_USER
        if [ -z "$PANEL_USER" ]; then
            echo -e "${RED}Username is required and cannot be empty.${NC}"
            continue
        fi
        echo -e "${GREEN}Admin username set to:${NC} ${YELLOW}$PANEL_USER${NC}\n"
        break
    done
    while true; do
        stty -echo
        printf "${CYAN}Enter admin password:${NC} "
        read -r PANEL_PASS
        echo ""
        printf "${CYAN}Confirm password:${NC} "
        read -r PANEL_PASS2
        stty echo
        echo ""
        if [ -z "$PANEL_PASS" ]; then
            echo -e "${RED}Password cannot be empty. Please try again.${NC}"
            echo ""
            continue
        fi
        if [ "$PANEL_PASS" != "$PANEL_PASS2" ]; then
            echo -e "${RED}Passwords do not match. Please try again.${NC}"
            echo ""
            continue
        fi
        break
    done
    while true; do
        echo -ne "${CYAN}Set session timeout (seconds) (default 3600):${NC} "
        read -r SESSION_TIMEOUT
        if [ -z "$SESSION_TIMEOUT" ]; then SESSION_TIMEOUT=3600; fi
        if [[ "$SESSION_TIMEOUT" =~ ^[0-9]+$ ]] && [ "$SESSION_TIMEOUT" -gt 0 ]; then
            echo -e "${GREEN}Session timeout set to:${NC} ${YELLOW}$SESSION_TIMEOUT${NC}\n"
            break
        fi
        echo -e "${RED}Please enter a positive number.${NC}"
    done

    while true; do
        echo -ne "${CYAN}Set max login attempts (default 3):${NC} "
        read -r MAX_LOGIN_ATTEMPTS
        if [ -z "$MAX_LOGIN_ATTEMPTS" ]; then MAX_LOGIN_ATTEMPTS=3; fi
        if [[ "$MAX_LOGIN_ATTEMPTS" =~ ^[0-9]+$ ]] && [ "$MAX_LOGIN_ATTEMPTS" -gt 0 ]; then
            echo -e "${GREEN}Max login attempts set to:${NC} ${YELLOW}$MAX_LOGIN_ATTEMPTS${NC}\n"
            break
        fi
        echo -e "${RED}Please enter a positive number.${NC}"
    done

    while true; do
        echo -ne "${CYAN}Set lockout duration (seconds) (default 300):${NC} "
        read -r LOCKOUT_DURATION
        if [ -z "$LOCKOUT_DURATION" ]; then LOCKOUT_DURATION=300; fi
        if [[ "$LOCKOUT_DURATION" =~ ^[0-9]+$ ]] && [ "$LOCKOUT_DURATION" -gt 0 ]; then
            echo -e "${GREEN}Lockout duration set to:${NC} ${YELLOW}$LOCKOUT_DURATION${NC}\n"
            break
        fi
        echo -e "${RED}Please enter a positive number.${NC}"
    done

    PYTHON_BIN="python3"
    if [ -f .venv/bin/python ]; then PYTHON_BIN=".venv/bin/python"; elif [ -f .venv/Scripts/python.exe ]; then PYTHON_BIN=".venv/Scripts/python"; fi
    WG_PANEL_USER="$PANEL_USER" WG_PANEL_PASS="$PANEL_PASS" WG_SESSION_TIMEOUT="$SESSION_TIMEOUT" WG_MAX_ATTEMPTS="$MAX_LOGIN_ATTEMPTS" WG_LOCKOUT="$LOCKOUT_DURATION" "$PYTHON_BIN" - << 'PYAUTH'
import json, os, stat
from argon2 import PasswordHasher
user=os.environ.get('WG_PANEL_USER')
pw=os.environ.get('WG_PANEL_PASS')
st=int(os.environ.get('WG_SESSION_TIMEOUT','3600'))
ma=int(os.environ.get('WG_MAX_ATTEMPTS','3'))
ld=int(os.environ.get('WG_LOCKOUT','300'))
if not user or not pw:
    raise SystemExit('Missing username or password for panel config')
ph=PasswordHasher()
cfg={'username': user,
     'password_hash': ph.hash(pw),
     'session_timeout': st,
     'max_login_attempts': ma,
     'lockout_duration': ld}
with open('auth_config.json','w',encoding='utf-8') as f:
    json.dump(cfg,f,indent=4)
try:
    if os.name=='posix':
        os.chmod('auth_config.json', 0o600)
except Exception:
    pass
PYAUTH

    clear
    cat > watchguard_service_panel.py << 'PYPANEL'
import asyncio, os
from uvicorn import Config, Server
from watchguard_web_dashboard import app

async def main():
    port = int(os.environ.get('WG_PANEL_PORT','8000'))
    cfg = Config(app=app, host='0.0.0.0', port=port, loop='asyncio', log_level='info')
    srv = Server(cfg)
    print(f"Web panel starting on http://0.0.0.0:{port}")
    await srv.serve()

if __name__=='__main__':
    asyncio.run(main())
PYPANEL

    chmod +x watchguard_service_panel.py

    if command -v systemctl >/dev/null 2>&1; then
        echo -e "${CYAN}Creating systemd service (watchguard-panel.service)...${NC}"
        svc_path="/etc/systemd/system/watchguard-panel.service"
        sudo bash -c "cat > $svc_path" << 'SVCPANEL'
[Unit]
Description=WatchGuard Web Panel
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=__WG_DIR__
Environment=VIRTUAL_ENV=__WG_DIR__/.venv
Environment=PATH=__WG_DIR__/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=WG_PANEL_PORT=__WG_PORT__
ExecStart=__WG_DIR__/.venv/bin/python __WG_DIR__/watchguard_service_panel.py
Restart=on-failure
RestartSec=2
StandardOutput=append:/var/log/watchguard-panel.log
StandardError=append:/var/log/watchguard-panel.log
User=root

[Install]
WantedBy=multi-user.target
SVCPANEL
        sed -i "s#__WG_DIR__#$(pwd)#g" "$svc_path"
        sed -i "s#__WG_PORT__#${PANEL_PORT}#g" "$svc_path"
        run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        run_with_spinner "Enabling panel service" systemctl enable watchguard-panel.service || true
        run_with_spinner "Starting panel service" systemctl restart watchguard-panel.service || true
        echo -e "${GREEN}Panel service is up.${NC}"
        echo -e "${WHITE}Logs:${NC} /var/log/watchguard-panel.log"
    else
        echo -e "${YELLOW}systemd not available; starting panel in background.${NC}"
        PYTHONDONTWRITEBYTECODE=1 WG_PANEL_PORT="$PANEL_PORT" nohup python3 watchguard_service_panel.py >/tmp/watchguard_panel.log 2>&1 &
        echo -e "${WHITE}Panel log:${NC} /tmp/watchguard_panel.log"
    fi

    echo ""
    read -rp "Enable HTTPS with Let's Encrypt for a domain? (y/n): " ENABLE_SSL
    if [[ "$ENABLE_SSL" =~ ^[Yy]$ ]]; then
        while true; do
            read -rp "Enter domain name (e.g., example.com): " PANEL_DOMAIN
            [ -n "$PANEL_DOMAIN" ] && break
            echo -e "${RED}Domain cannot be empty.${NC}"
        done
        while true; do
            read -rp "Enter admin email for Let's Encrypt: " LE_EMAIL
            [ -n "$LE_EMAIL" ] && break
            echo -e "${RED}Email cannot be empty.${NC}"
        done

        if command -v apt-get >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y certbot >/dev/null 2>&1" || true
        elif command -v dnf >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "dnf install -y certbot >/dev/null 2>&1" || true
        elif command -v yum >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "yum install -y certbot >/dev/null 2>&1" || true
        elif command -v pacman >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "pacman -Sy --noconfirm certbot >/dev/null 2>&1" || true
        fi

        echo -e "${YELLOW}Certbot will bind to port 80 temporarily. Ensure it's free.${NC}"
        if certbot certonly --standalone -d "${PANEL_DOMAIN}" -m "${LE_EMAIL}" --agree-tos --no-eff-email --non-interactive; then
            CERT_DIR="/etc/letsencrypt/live/${PANEL_DOMAIN}"
            CERT_FILE="${CERT_DIR}/fullchain.pem"
            KEY_FILE="${CERT_DIR}/privkey.pem"
            if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
                python3 - << PYSSL
import json
try:
    with open('settings.json','r',encoding='utf-8') as f:
        data=json.load(f)
except Exception:
    data={}
data['ssl_certfile'] = r'${CERT_FILE}'
data['ssl_keyfile'] = r'${KEY_FILE}'
with open('settings.json','w',encoding='utf-8') as f:
    json.dump(data,f,indent=4)
PYSSL
                echo -e "${GREEN}Certificates installed and saved to settings.json.${NC}"
                if command -v systemctl >/dev/null 2>&1; then
                    systemctl restart watchguard-panel.service || true
                else
                    OLD_PORT=""
                    for pid in $(pgrep -f "watchguard_service_panel.py|uvicorn.*watchguard_web_dashboard:app" 2>/dev/null); do
                        if [ -r "/proc/$pid/environ" ]; then
                            ENVSTR=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep '^WG_PANEL_PORT=' || true)
                            if [ -n "$ENVSTR" ]; then
                                OLD_PORT="${ENVSTR#WG_PANEL_PORT=}"
                                break
                            fi
                        fi
                    done
                    [ -z "$OLD_PORT" ] && OLD_PORT=8000
                    pkill -f "watchguard_service_panel.py" >/dev/null 2>&1 || true
                    pkill -f "uvicorn.*watchguard_web_dashboard:app" >/dev/null 2>&1 || true
                    PYTHONDONTWRITEBYTECODE=1 WG_PANEL_PORT="$OLD_PORT" nohup python3 watchguard_service_panel.py >/tmp/watchguard_panel.log 2>&1 &
                fi
                clear
                local width=68
                local URL="https://${PANEL_DOMAIN}:${PANEL_PORT}"
                echo -e "${LGREEN}"
                printf "┌%s┐\n" "$(printf '─%.0s' $(seq 1 $width))"
                printf "│%-${width}s│\n" ""
                printf "│%-${width}s│\n" "  To access the Web Panel, open the following URL:"
                printf "│%-${width}s│\n" "  ${URL}"
                printf "│%-${width}s│\n" ""
                printf "└%s┘\n" "$(printf '─%.0s' $(seq 1 $width))"
                echo -e "${NC}"
                create_cli_launcher
                echo -ne "${CYAN}Press Enter to return to main menu...${NC} "
                read -r
                SKIP_WAIT=1
                return
            fi
        else
            echo -e "${RED}Standalone failed (port 80 busy?).${NC}"
            read -rp "Try DNS-01 manual challenge instead? (y/n): " TRY_DNS2
            if [[ "$TRY_DNS2" =~ ^[Yy]$ ]]; then
                if certbot -d "${PANEL_DOMAIN}" --manual --preferred-challenges dns certonly -m "${LE_EMAIL}" --agree-tos --no-eff-email --manual-public-ip-logging-ok; then
                    CERT_DIR="/etc/letsencrypt/live/${PANEL_DOMAIN}"
                    CERT_FILE="${CERT_DIR}/fullchain.pem"
                    KEY_FILE="${CERT_DIR}/privkey.pem"
                    if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
                        python3 - << PYSSL2
import json
try:
    with open('settings.json','r',encoding='utf-8') as f:
        data=json.load(f)
except Exception:
    data={}
data['ssl_certfile'] = r'${CERT_FILE}'
data['ssl_keyfile'] = r'${KEY_FILE}'
with open('settings.json','w',encoding='utf-8') as f:
    json.dump(data,f,indent=4)
PYSSL2
                        echo -e "${GREEN}Certificates installed and saved to settings.json.${NC}"
                        if command -v systemctl >/dev/null 2>&1; then
                            systemctl restart watchguard-panel.service || true
                        fi
                    fi
                else
                    echo -e "${RED}DNS-01 flow failed or was cancelled.${NC}"
                fi
            fi
        fi
    fi
    clear
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(ip -4 addr show scope global 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)
    fi
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP="127.0.0.1"
    fi
    local width=68
    local URL="http://${SERVER_IP}:${PANEL_PORT}"
    echo -e "${LGREEN}"
    printf "┌%s┐\n" "$(printf '─%.0s' $(seq 1 $width))"
    printf "│%-${width}s│\n" ""
    printf "│%-${width}s│\n" "  To access the Web Panel, open the following URL:"
    printf "│%-${width}s│\n" "  ${URL}"
    printf "│%-${width}s│\n" ""
    printf "└%s┘\n" "$(printf '─%.0s' $(seq 1 $width))"
    echo -e "${NC}"
    create_cli_launcher
    echo -ne "${CYAN}Press Enter to return to main menu...${NC} "
    read -r
    SKIP_WAIT=1
}

install_watchguard_suite() {
    clear
    echo -e "${BOLD}${GREEN}Preparing to install Web Panel + Bot...${NC}"

    if command -v apt-get >/dev/null 2>&1; then
        run_with_spinner "Updating package index (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1" || true
        run_with_spinner "Installing Python build deps (apt)" bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip build-essential python3-dev libffi-dev >/dev/null 2>&1" || true
    elif command -v dnf >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (dnf)" bash -c "dnf install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v yum >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (yum)" bash -c "yum install -y python3 python3-pip gcc python3-devel libffi-devel >/dev/null 2>&1" || true
    elif command -v pacman >/dev/null 2>&1; then
        run_with_spinner "Installing Python build deps (pacman)" bash -c "pacman -Sy --noconfirm python python-pip base-devel libffi >/dev/null 2>&1" || true
    fi

    is_bot_installed && stop_and_remove_bot_service || true
    is_panel_installed && stop_and_remove_panel_service || true

    if [ ! -d .venv ]; then
        run_with_spinner "Creating virtual environment (.venv)" python3 -m venv .venv || true
    fi
    if [ -f .venv/bin/activate ]; then . .venv/bin/activate; elif [ -f .venv/Scripts/activate ]; then . .venv/Scripts/activate; fi
    if command -v pip >/dev/null 2>&1; then
        run_with_spinner "Upgrading pip" bash -c "pip install --upgrade pip >/dev/null 2>&1" || true
        run_with_spinner "Installing Python dependencies" bash -c "pip install -r requirements.txt >/dev/null 2>&1" || true
        run_with_spinner "Ensuring argon2-cffi installed" bash -c "pip install -q argon2-cffi >/dev/null 2>&1" || true
    fi

    clear

    NEED_BOT=0
    if ! python3 - << 'PYBOTCHK' >/dev/null 2>&1
import json
ok=False
try:
    with open('config.json','r',encoding='utf-8') as f:
        d=json.load(f)
    tok=(d.get('TOKEN') or '').strip()
    ids=d.get('CHAT_IDS') or []
    ok=bool(tok) and bool(ids)
except Exception:
    ok=False
print('OK' if ok else 'NO')
exit(0 if ok else 1)
PYBOTCHK
    then
        NEED_BOT=1
    fi

    if [ "$NEED_BOT" = "1" ]; then
        while true; do
            echo -ne "${BOLD}Enter your ${LGREEN}Telegram Bot Token${NC}: "
            read -r INSTALL_TOKEN
            if [ -z "$INSTALL_TOKEN" ]; then
                echo -e "${RED}Bot Token cannot be empty. Please enter a valid token.${NC}"
                continue
            fi
            if [[ ! "$INSTALL_TOKEN" =~ ^[0-9]{6,10}:[A-Za-z0-9_-]{20,}$ ]]; then
                echo -e "${RED}Token format looks invalid. Please provide a valid token.${NC}"
                continue
            fi
            if command -v curl >/dev/null 2>&1; then
                echo -ne "${PURPLE}Validating token with Telegram${NC}"
                for i in 1 2 3; do echo -n "."; sleep 0.2; done
                echo ""
                if ! curl -s "https://api.telegram.org/bot${INSTALL_TOKEN}/getMe" | grep -q '"ok":true'; then
                    echo -e "${RED}The token appears to be invalid or unreachable. Please provide a valid token.${NC}"
                    continue
                fi
            fi
            break
        done

        echo ""
        while true; do
            echo -ne "${BOLD}Enter ${LGREEN}Telegram Chat ID(s)${NC} (comma separated): "
            read -r INSTALL_CHAT_IDS
            if [ -z "$INSTALL_CHAT_IDS" ]; then
                echo -e "${RED}Chat ID(s) cannot be empty. Please enter at least one numeric ID.${NC}"
                continue
            fi
            OLDIFS="$IFS"; IFS=','
            valid_ids=1
            for raw in $INSTALL_CHAT_IDS; do
                id="${raw//[[:space:]]/}"
                if ! [[ "$id" =~ ^[0-9]+$ ]]; then
                    valid_ids=0; break
                fi
            done
            IFS="$OLDIFS"
            if [ $valid_ids -eq 0 ]; then
                echo -e "${RED}Invalid Chat ID(s). Only digits are allowed, separated by commas.${NC}"
                continue
            fi
            break
        done

        python3 - "$INSTALL_TOKEN" "$INSTALL_CHAT_IDS" << 'PYBOTCONF3'
import json, sys
path = 'config.json'
token = sys.argv[1]
chat_ids_raw = sys.argv[2]
ids = []
for part in chat_ids_raw.split(','):
    p = part.strip()
    if not p:
        continue
    try:
        ids.append(int(p))
    except Exception:
        ids.append(p)
data = {}
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    data = {}
data['TOKEN'] = token
data['CHAT_IDS'] = ids
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
PYBOTCONF3
    fi

    NEED_AUTH=1

    if [ "$NEED_AUTH" = "1" ]; then
        echo ""
        echo -e "${BOLD}Configure ${YELLOW}Web Panel${NC} admin credentials"
        while true; do
            echo -ne "${BOLD}Enter admin ${LGREEN}username${NC}: "
            read -r PANEL_USER
            [ -n "$PANEL_USER" ] && break
            echo -e "${RED}Username cannot be empty.${NC}"
        done
        while true; do
            stty -echo
            printf "${BOLD}Enter admin ${RED}password${NC}: "
            read -r PANEL_PASS
            echo ""
            printf "${BOLD}Confirm ${RED}password${NC}: "
            read -r PANEL_PASS2
            stty echo
            echo ""
            [ -z "$PANEL_PASS" ] && { echo -e "${RED}Password cannot be empty.${NC}"; continue; }
            [ "$PANEL_PASS" != "$PANEL_PASS2" ] && { echo -e "${RED}Passwords do not match.${NC}"; continue; }
            break
        done
        SESSION_TIMEOUT=3600
        MAX_LOGIN_ATTEMPTS=3
        LOCKOUT_DURATION=300
        WG_PANEL_USER="$PANEL_USER" WG_PANEL_PASS="$PANEL_PASS" WG_SESSION_TIMEOUT="$SESSION_TIMEOUT" WG_MAX_ATTEMPTS="$MAX_LOGIN_ATTEMPTS" WG_LOCKOUT="$LOCKOUT_DURATION" python3 - << 'PYAUTH'
import json, os
from argon2 import PasswordHasher
user=os.environ.get('WG_PANEL_USER')
pw=os.environ.get('WG_PANEL_PASS')
st=int(os.environ.get('WG_SESSION_TIMEOUT','3600'))
ma=int(os.environ.get('WG_MAX_ATTEMPTS','3'))
ld=int(os.environ.get('WG_LOCKOUT','300'))
ph=PasswordHasher()
cfg={'username': user,
     'password_hash': ph.hash(pw),
     'session_timeout': st,
     'max_login_attempts': ma,
     'lockout_duration': ld}
with open('auth_config.json','w',encoding='utf-8') as f:
    json.dump(cfg,f,indent=4)
try:
    if os.name=='posix':
        os.chmod('auth_config.json', 0o600)
except Exception:
    pass
PYAUTH
    fi

    echo ""
    while true; do
        echo -ne "${BOLD}Enter ${YELLOW}port${NC} for Web Panel (default 8000): "
        read -r PANEL_PORT
        [ -z "$PANEL_PORT" ] && PANEL_PORT=8000
        if ! [[ "$PANEL_PORT" =~ ^[0-9]+$ ]] || [ "$PANEL_PORT" -lt 1 ] || [ "$PANEL_PORT" -gt 65535 ]; then
            echo -e "${RED}Invalid port. Please enter a number between 1 and 65535.${NC}"
            continue
        fi
        if command -v ss >/dev/null 2>&1; then
            if ss -ltnp 2>/dev/null | awk '{print $4" "$6}' | grep -E ":${PANEL_PORT}( |$)" >/dev/null 2>&1; then
                echo -e "${RED}This port is currently in use by another process. Please choose another port.${NC}"
                continue
            fi
        elif command -v lsof >/dev/null 2>&1; then
            if lsof -i TCP:"${PANEL_PORT}" -sTCP:LISTEN >/dev/null 2}&1; then
                echo -e "${RED}This port is currently in use by another process. Please choose another port.${NC}"
                continue
            fi
        fi
        if python3 - "$PANEL_PORT" << 'PYPORT'
import sys, socket
try:
    p = int(sys.argv[1])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", p))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PYPORT
        then
            echo -e "${GREEN}Panel port set to:${NC} ${YELLOW}$PANEL_PORT${NC}\n"
            break
        else
            echo -e "${RED}This port is already in use. Please choose another port.${NC}"
        fi
    done

    cat > watchguard_service_suite.py << 'PYSUITE'
import asyncio, os, threading, json
from uvicorn import Config, Server
from watchguard_web_dashboard import app
from watchguard_bot import setup_bot

PORT = int(os.environ.get('WG_PANEL_PORT', '8000'))

def run_web():
    ssl_kwargs = {}
    try:
        with open('settings.json','r',encoding='utf-8') as f:
            s=json.load(f)
        cert=(s.get('ssl_certfile') or '').strip()
        key=(s.get('ssl_keyfile') or '').strip()
        if cert and key:
            ssl_kwargs={'ssl_certfile': cert, 'ssl_keyfile': key}
    except Exception:
        pass
    config = Config(app=app, host="0.0.0.0", port=PORT, loop="asyncio", log_level="info", **ssl_kwargs)
    server = Server(config)
    asyncio.run(server.serve())

def run_bot():
    setup_bot()

if __name__ == '__main__':
    t = threading.Thread(target=run_web, daemon=True)
    t.start()
    run_bot()
PYSUITE
    chmod +x watchguard_service_suite.py

    if command -v systemctl >/dev/null 2>&1; then
        echo -e "${CYAN}Creating systemd service (watchguard.service)...${NC}"
        svc_path="/etc/systemd/system/watchguard.service"
        sudo bash -c "cat > $svc_path" << 'SVCSUITE'
[Unit]
Description=WatchGuard Suite (Web Panel + Bot)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=__WG_DIR__
Environment=VIRTUAL_ENV=__WG_DIR__/.venv
Environment=PATH=__WG_DIR__/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=WG_PANEL_PORT=__WG_PORT__
ExecStart=__WG_DIR__/.venv/bin/python __WG_DIR__/watchguard_service_suite.py
Restart=on-failure
RestartSec=2
StandardOutput=append:/var/log/watchguard.log
StandardError=append:/var/log/watchguard.log
User=root

[Install]
WantedBy=multi-user.target
SVCSUITE
        sed -i "s#__WG_DIR__#$(pwd)#g" "$svc_path"
        sed -i "s#__WG_PORT__#${PANEL_PORT}#g" "$svc_path"
        run_with_spinner "Reloading systemd" systemctl daemon-reload || true
        run_with_spinner "Enabling suite service" systemctl enable watchguard.service || true
        run_with_spinner "Starting suite service" systemctl restart watchguard.service || true
        echo -e "${GREEN}WatchGuard (Web Panel + Bot) service is up.${NC}"
        echo -e "${WHITE}Logs:${NC} /var/log/watchguard.log"
    else
        echo -e "${YELLOW}systemd not available; starting suite in background.${NC}"
        WG_PANEL_PORT="$PANEL_PORT" nohup python3 watchguard_service_suite.py >/tmp/watchguard_suite.log 2>&1 &
        echo -e "${WHITE}Suite log:${NC} /tmp/watchguard_suite.log"
    fi

    echo ""
    read -rp "Enable HTTPS with Let's Encrypt for a domain? (y/n): " ENABLE_SSL
    if [[ "$ENABLE_SSL" =~ ^[Yy]$ ]]; then
        while true; do
            read -rp "Enter domain name (e.g., example.com): " PANEL_DOMAIN
            [ -n "$PANEL_DOMAIN" ] && break
            echo -e "${RED}Domain cannot be empty.${NC}"
        done
        while true; do
            read -rp "Enter admin email for Let's Encrypt: " LE_EMAIL
            [ -n "$LE_EMAIL" ] && break
            echo -e "${RED}Email cannot be empty.${NC}"
        done

        if command -v apt-get >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "DEBIAN_FRONTEND=noninteractive apt-get install -y certbot >/dev/null 2>&1" || true
        elif command -v dnf >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "dnf install -y certbot >/dev/null 2>&1" || true
        elif command -v yum >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "yum install -y certbot >/dev/null 2>&1" || true
        elif command -v pacman >/dev/null 2>&1; then
            run_with_spinner "Installing certbot" bash -c "pacman -Sy --noconfirm certbot >/dev/null 2>&1" || true
        fi
        if certbot certonly --standalone -d "${PANEL_DOMAIN}" -m "${LE_EMAIL}" --agree-tos --no-eff-email --non-interactive; then
            CERT_DIR="/etc/letsencrypt/live/${PANEL_DOMAIN}"
            CERT_FILE="${CERT_DIR}/fullchain.pem"
            KEY_FILE="${CERT_DIR}/privkey.pem"
            if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
                python3 - << PYSSL2
import json
try:
    with open('settings.json','r',encoding='utf-8') as f:
        data=json.load(f)
except Exception:
    data={}
data['ssl_certfile'] = r'${CERT_FILE}'
data['ssl_keyfile'] = r'${KEY_FILE}'
with open('settings.json','w',encoding='utf-8') as f:
    json.dump(data,f,indent=4)
PYSSL2
                echo -e "${GREEN}Certificates installed and saved to settings.json.${NC}"
                if command -v systemctl >/dev/null 2>&1; then
                    systemctl restart watchguard.service || true
                else
                    OLD_PORT=""
                    for pid in $(pgrep -f "watchguard_service_panel.py|uvicorn.*watchguard_web_dashboard:app" 2>/dev/null); do
                        if [ -r "/proc/$pid/environ" ]; then
                            ENVSTR=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep '^WG_PANEL_PORT=' || true)
                            if [ -n "$ENVSTR" ]; then
                                OLD_PORT="${ENVSTR#WG_PANEL_PORT=}"
                                break
                            fi
                        fi
                    done
                    [ -z "$OLD_PORT" ] && OLD_PORT=8000
                    pkill -f "watchguard_service_panel.py" >/dev/null 2>&1 || true
                    pkill -f "uvicorn.*watchguard_web_dashboard:app" >/dev/null 2>&1 || true
                    WG_PANEL_PORT="$OLD_PORT" nohup python3 watchguard_service_panel.py >/tmp/watchguard_panel.log 2>&1 &
                fi
                clear
                local width=68
                local URL="https://${PANEL_DOMAIN}:${PANEL_PORT}"
                echo -e "${LGREEN}"
                printf "┌%s┐\n" "$(printf '─%.0s' $(seq 1 $width))"
                printf "│%-${width}s│\n" ""
                printf "│%-${width}s│\n" "  To access the Web Panel, open the following URL:"
                printf "│%-${width}s│\n" "  ${URL}"
                printf "│%-${width}s│\n" ""
                printf "└%s┘\n" "$(printf '─%.0s' $(seq 1 $width))"
                echo -e "${NC}"
                create_cli_launcher
                echo -ne "${CYAN}Press Enter to return to main menu...${NC} "
                read -r
                SKIP_WAIT=1
                return
            fi
        else
            echo -e "${RED}Certbot failed. Keeping HTTP for now.${NC}"
        fi
    fi

    clear
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(ip -4 addr show scope global 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)
    fi
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP="127.0.0.1"
    fi
    local width=68
    local URL="http://${SERVER_IP}:${PANEL_PORT}"
    echo -e "${LGREEN}"
    printf "┌%s┐\n" "$(printf '─%.0s' $(seq 1 $width))"
    printf "│%-${width}s│\n" ""
    printf "│%-${width}s│\n" "  To access the Web Panel, open the following URL:"
    printf "│%-${width}s│\n" "  ${URL}"
    printf "│%-${width}s│\n" ""
    printf "└%s┘\n" "$(printf '─%.0s' $(seq 1 $width))"
    echo -e "${NC}"
    create_cli_launcher
    echo -ne "${CYAN}Press Enter to return to main menu...${NC} "
    read -r
    SKIP_WAIT=1
}
uninstall_watchguard() {
    clear
    echo -e "${BOLD}${WHITE}Remove WatchGuard Components${NC}"

    while true; do
        HAS_BOT=0; is_bot_installed && HAS_BOT=1
        HAS_PANEL=0; is_panel_installed && HAS_PANEL=1
        HAS_SUITE=0; is_suite_installed && HAS_SUITE=1

        OPT1_ENABLED=0
        if [ "$HAS_BOT" -eq 1 ] && [ "$HAS_PANEL" -eq 0 ] && [ "$HAS_SUITE" -eq 0 ]; then
            OPT1_ENABLED=1
        fi

        OPT2_ENABLED=0
        if [ "$HAS_PANEL" -eq 1 ] || [ "$HAS_SUITE" -eq 1 ]; then
            OPT2_ENABLED=1
        fi

        OPT3_ENABLED=0
        if [ "$HAS_SUITE" -eq 1 ] || { [ "$HAS_BOT" -eq 1 ] && [ "$HAS_PANEL" -eq 1 ]; }; then
            OPT3_ENABLED=1
        fi

        echo -e " ${GREEN}[1]${NC} Remove Telegram Bot"
        echo -e " ${YELLOW}[2]${NC} Remove Web Panel"
        echo -e " ${PURPLE}[3]${NC} Remove Bot + Panel"
        echo -e " ${RED}[4]${NC} Remove Entire WatchGuard Project"
        echo -e " ${CYAN}[5]${NC} Return to Previous Menu"
        echo -ne "${CYAN}Choose [1-5]: ${NC}"
        read -r rmchoice
        if [ -z "$rmchoice" ]; then
            echo -e "${RED}You must choose an option (1-5)${NC}"
            echo ""
            sleep 2
            clear
            continue
        fi
        if [ "$rmchoice" = "1" ] && [ "$OPT1_ENABLED" -ne 1 ]; then
            echo -e "${YELLOW}Option 1 is unavailable (bot not installed or panel/suite present).${NC}"
            echo ""; sleep 2; clear; continue
        fi
        if [ "$rmchoice" = "2" ] && [ "$OPT2_ENABLED" -ne 1 ]; then
            echo -e "${YELLOW}Option 2 is unavailable (panel/suite not installed).${NC}"
            echo ""; sleep 2; clear; continue
        fi
        if [ "$rmchoice" = "3" ] && [ "$OPT3_ENABLED" -ne 1 ]; then
            echo -e "${YELLOW}Option 3 is unavailable (neither suite nor both components installed).${NC}"
            echo ""; sleep 2; clear; continue
        fi
        if [[ "$rmchoice" =~ ^[1-5]$ ]]; then break; fi
        echo -e "${RED}Invalid choice. Please enter 1, 2, 3, 4, or 5${NC}"
        echo ""
        sleep 2
        clear
    done

    is_bot_installed() {
        if command -v systemctl >/dev/null 2>&1; then
            systemctl list-unit-files | grep -q "^watchguard-bot\.service" && return 0
            systemctl list-unit-files | grep -q "^watchguard\.service" && return 0
            [ -f /etc/systemd/system/watchguard-bot.service ] && return 0
            [ -f /etc/systemd/system/watchguard.service ] && return 0
        fi
        pgrep -f "watchguard_service_suite.py|watchguard_service_bot.py|watchguard_launcher.py|watchguard_launcher.sh|watchguard_bot.py|uvicorn.*watchguard_web_dashboard:app" >/dev/null 2>&1 && return 0
        return 1
    }

    is_panel_installed() {
        if command -v systemctl >/dev/null 2>&1; then
            systemctl list-unit-files | grep -q "^watchguard-panel\.service" && return 0
            systemctl list-unit-files | grep -q "^watchguard\.service" && return 0
            [ -f /etc/systemd/system/watchguard-panel.service ] && return 0
            [ -f /etc/systemd/system/watchguard.service ] && return 0
        fi
        pgrep -f "watchguard_service_suite.py|watchguard_service_panel.py|watchguard_web_dashboard.py|uvicorn.*watchguard_web_dashboard:app" >/dev/null 2>&1 && return 0
        return 1
    }

    remove_bot_service() {
        if command -v systemctl >/dev/null 2>&1; then
            if systemctl list-units --type=service --all | grep -q watchguard-bot.service; then
                run_with_spinner "Stopping bot service" systemctl stop watchguard-bot.service || true
                run_with_spinner "Disabling bot service" systemctl disable watchguard-bot.service || true
            fi
            if [ -f /etc/systemd/system/watchguard-bot.service ]; then
                run_with_spinner "Removing bot service file" rm -f /etc/systemd/system/watchguard-bot.service || true
                run_with_spinner "Reloading systemd" systemctl daemon-reload || true
            fi
        fi
        pkill -f "watchguard_service_bot.py" >/dev/null 2>&1 || true
        pkill -f "watchguard_launcher.py" >/dev/null 2>&1 || true
        pkill -f "watchguard_bot.py" >/dev/null 2>&1 || true
        [ -f /var/log/watchguard-bot.log ] && run_with_spinner "Removing bot log" rm -f /var/log/watchguard-bot.log || true
        [ -f /tmp/watchguard_bot.log ] && run_with_spinner "Removing bot temp log" rm -f /tmp/watchguard_bot.log || true
    }

    remove_panel_service() {
        if command -v systemctl >/dev/null 2>&1; then
            if systemctl list-units --type=service --all | grep -q watchguard-panel.service; then
                run_with_spinner "Stopping panel service" systemctl stop watchguard-panel.service || true
                run_with_spinner "Disabling panel service" systemctl disable watchguard-panel.service || true
            fi
            if [ -f /etc/systemd/system/watchguard-panel.service ]; then
                run_with_spinner "Removing panel service file" rm -f /etc/systemd/system/watchguard-panel.service || true
                run_with_spinner "Reloading systemd" systemctl daemon-reload || true
            fi
        fi
        pkill -f "watchguard_service_panel.py" >/dev/null 2>&1 || true
        pkill -f "watchguard_web_dashboard.py" >/dev/null 2>&1 || true
        pkill -f "uvicorn.*watchguard_web_dashboard:app" >/dev/null 2>&1 || true
        if [ -f auth_config.json ]; then
            run_with_spinner "Removing panel credentials file" rm -f auth_config.json || true
        fi
        [ -f /var/log/watchguard-panel.log ] && run_with_spinner "Removing panel log" rm -f /var/log/watchguard-panel.log || true
        [ -f /tmp/watchguard_panel.log ] && run_with_spinner "Removing panel temp log" rm -f /tmp/watchguard_panel.log || true
    }

    case $rmchoice in
        1)
            clear
            if is_suite_installed || is_panel_installed; then
                echo -e "\n${RED}You cannot remove the Telegram Bot while the Web Panel is installed.${NC}"
                echo -e "${YELLOW}Note:${NC} Removing the bot would disable Telegram notifications.\nPlease remove ${BOLD}Bot + Panel${NC} instead."
                echo -ne "\n${CYAN}Press Enter to continue...${NC} "
                read -r
                SKIP_WAIT=1
                clear
                uninstall_watchguard
                return
            fi
            if ! is_bot_installed; then
                echo -e "${YELLOW}Bot is not installed or running.${NC}"
                echo -ne "${CYAN}Press Enter to continue...${NC} "
                read -r
                SKIP_WAIT=1
                clear
                uninstall_watchguard
                return
            fi
            remove_bot_service
            reset_data_files_prompt
            ;;
        2)
            clear
            if is_suite_installed; then
                echo -e "${CYAN}Suite detected. Switching to Bot-only service...${NC}"
                stop_and_remove_suite_service
                create_bot_service_quick
                if [ -f auth_config.json ]; then
                    run_with_spinner "Removing panel credentials file" rm -f auth_config.json || true
                fi
                [ -f /var/log/watchguard-panel.log ] && run_with_spinner "Removing panel log" rm -f /var/log/watchguard-panel.log || true
                [ -f /tmp/watchguard_panel.log ] && run_with_spinner "Removing panel temp log" rm -f /tmp/watchguard_panel.log || true
            else
                if ! is_panel_installed; then
                    echo -e "${YELLOW}Web Panel is not installed or running.${NC}"
                    echo -ne "${CYAN}Press Enter to continue...${NC} "
                    read -r
                    SKIP_WAIT=1
                    clear
                    uninstall_watchguard
                    return
                fi
                remove_panel_service
            fi
            reset_data_files_prompt
            ;;
        3)
            clear
            if is_suite_installed; then
                stop_and_remove_suite_service
            fi
            remove_bot_service
            remove_panel_service
            reset_data_files_prompt
            ;;
        4)
            clear
            remove_entire_project
            return
            ;;
        5)
            SKIP_WAIT=1
            return
            ;;
    esac

    if [ "$rmchoice" = "1" ] || [ "$rmchoice" = "3" ]; then
        if [ -f config.json ]; then
            if ask_yes_no "Remove config.json?" "Y"; then
                run_with_spinner "Removing config.json" rm -f config.json || true
            fi
        fi
    fi

    if [ -d .venv ]; then
        if ask_yes_no "Remove virtual environment (.venv)?" "Y"; then
            run_with_spinner "Removing .venv" rm -rf .venv || true
        fi
    fi

    echo -e "${GREEN}Uninstall completed.${NC}"
}

change_bot_token_chat_ids() {
    clear
    echo -e "${BOLD}${CYAN}Change Bot Token & Chat IDs${NC}"
    echo ""

    if ! is_bot_installed && ! is_suite_installed; then
        echo -e "${RED}Bot is not installed. Please install the Telegram Bot first (option 1 or 2).${NC}"
        echo -ne "\n${CYAN}Press Enter to return to main menu...${NC} "
        read -r
        SKIP_WAIT=1
        return
    fi

    while true; do
        echo -ne "Enter Telegram Bot Token: "
        read -r NEW_TOKEN
        if [ -z "$NEW_TOKEN" ]; then
            echo -e "${RED}Bot Token cannot be empty. Please enter a valid token.${NC}"
            continue
        fi
        if [[ ! "$NEW_TOKEN" =~ ^[0-9]{6,10}:[A-Za-z0-9_-]{20,}$ ]]; then
            echo -e "${RED}Token format looks invalid. Please provide a valid token.${NC}"
            continue
        fi
        if command -v curl >/dev/null 2>&1; then
            echo -e "${CYAN}Validating token with Telegram...${NC}"
            if ! curl -s "https://api.telegram.org/bot${NEW_TOKEN}/getMe" | grep -q '"ok":true'; then
                echo -e "${RED}The token appears to be invalid or unreachable. Please provide a valid token.${NC}"
                continue
            fi
        fi
        break
    done

    while true; do
        echo -ne "Enter Telegram Chat ID(s) (comma separated): "
        read -r NEW_CHAT_IDS
        if [ -z "$NEW_CHAT_IDS" ]; then
            echo -e "${RED}Chat ID(s) cannot be empty. Please enter at least one numeric ID.${NC}"
            continue
        fi
        OLDIFS="$IFS"; IFS=','
        valid_ids=1
        for raw in $NEW_CHAT_IDS; do
            id="${raw//[[:space:]]/}"
            if ! [[ "$id" =~ ^[0-9]+$ ]]; then
                valid_ids=0; break
            fi
        done
        IFS="$OLDIFS"
        if [ $valid_ids -eq 0 ]; then
            echo -e "${RED}Invalid Chat ID(s). Only digits are allowed, separated by commas.${NC}"
            continue
        fi
        break
    done

    python3 - "$NEW_TOKEN" "$NEW_CHAT_IDS" << 'PYBOTWRITE'
import json, sys
path = 'config.json'
token = sys.argv[1]
chat_ids_raw = sys.argv[2]
ids = []
for part in chat_ids_raw.split(','):
    p = part.strip()
    if not p:
        continue
    try:
        ids.append(int(p))
    except Exception:
        ids.append(p)
data = {}
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    data = {}
data['TOKEN'] = token
data['CHAT_IDS'] = ids
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
PYBOTWRITE

    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files | grep -q '^watchguard\.service'; then
            run_with_spinner "Restarting suite service" systemctl restart watchguard.service || true
        elif systemctl list-unit-files | grep -q '^watchguard-bot\.service'; then
            run_with_spinner "Restarting bot service" systemctl restart watchguard-bot.service || true
        fi
    fi

    echo -e "${GREEN}Bot configuration updated successfully.${NC}"
}

change_web_panel_credentials() {
    clear
    echo -e "${BOLD}${WHITE}Change Web Panel Credentials${NC}"
    echo ""

    if ! is_panel_installed && ! is_suite_installed; then
        echo -e "${RED}Web Panel is not installed. Please install the Web Panel first (option 2).${NC}"
        echo -ne "\n${CYAN}Press Enter to return to main menu...${NC} "
        read -r
        SKIP_WAIT=1
        return
    fi

    while true; do
        echo -ne "${WHITE}${BOLD}Enter admin ${LGREEN}username${NC}${WHITE}:${NC} "
        read -r NEW_USER
        [ -n "$NEW_USER" ] && break
        echo -e "${RED}Username cannot be empty.${NC}"
    done

    while true; do
        stty -echo
        printf "${WHITE}${BOLD}Enter admin ${RED}password${NC}${WHITE}:${NC} "
        read -r NEW_PASS
        echo ""
        printf "${WHITE}${BOLD}Confirm ${RED}password${NC}${WHITE}:${NC} "
        read -r NEW_PASS2
        stty echo
        echo ""
        [ -z "$NEW_PASS" ] && { echo -e "${RED}Password cannot be empty.${NC}"; continue; }
        [ "$NEW_PASS" != "$NEW_PASS2" ] && { echo -e "${RED}Passwords do not match.${NC}"; continue; }
        break
    done

    PYTHON_BIN="python3"
    if [ -f .venv/bin/python ]; then PYTHON_BIN=".venv/bin/python"; elif [ -f .venv/Scripts/python.exe ]; then PYTHON_BIN=".venv/Scripts/python"; fi
    WG_PANEL_USER="$NEW_USER" WG_PANEL_PASS="$NEW_PASS" "$PYTHON_BIN" - << 'PYPW'
import json, os
from argon2 import PasswordHasher
user=os.environ.get('WG_PANEL_USER')
pw=os.environ.get('WG_PANEL_PASS')
ph=PasswordHasher()
cfg={}
try:
    with open('auth_config.json','r',encoding='utf-8') as f:
        cfg=json.load(f)
except Exception:
    cfg={}
cfg['username']=user
cfg['password_hash']=ph.hash(pw)
cfg.setdefault('session_timeout', 3600)
cfg.setdefault('max_login_attempts', 3)
cfg.setdefault('lockout_duration', 300)
with open('auth_config.json','w',encoding='utf-8') as f:
    json.dump(cfg,f,indent=4)
try:
    if os.name=='posix':
        os.chmod('auth_config.json', 0o600)
except Exception:
    pass
PYPW

    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files | grep -q '^watchguard\.service'; then
            run_with_spinner "Restarting suite service" systemctl restart watchguard.service || true
        elif systemctl list-unit-files | grep -q '^watchguard-panel\.service'; then
            run_with_spinner "Restarting panel service" systemctl restart watchguard-panel.service || true
        fi
    fi

    echo -e "${GREEN}Web Panel credentials updated successfully.${NC}"
}

reset_data_files_prompt() {
    clear
    if ! ask_yes_no "Reset data files (servers/domains/labels/settings) to defaults?" "Y"; then
        return
    fi
    python3 - << 'PYRESETALL'
import json, os, datetime

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

now = datetime.datetime.now().isoformat()

write_json('labels.json', {
    'labels': ['watchguard'],
    'created_at': now,
    'last_updated': now,
    'version': '1.0'
})

write_json('servers.json', {})
write_json('domains.json', {})

write_json('settings.json', {
    'warning_days': 5,
    'notification_hour': 9,
    'notification_minute': 0,
    'daily_notifications': True,
    'web_panel_enabled': False,
    'labels': ['watchguard']
})
print('Data files reset to defaults')
PYRESETALL
}

remove_entire_project() {
    echo -e "${BOLD}${RED}WARNING:${NC} This will permanently delete the entire project directory:"
    echo -e "${YELLOW}$(pwd)${NC}"
    echo -ne "Type ${RED}DELETE${NC} to confirm: "
    read -r CONF
    if [ "$CONF" != "DELETE" ]; then
        echo -e "${YELLOW}Cancelled.${NC}"
        return
    fi

    is_bot_installed && remove_bot_service || true
    is_panel_installed && remove_panel_service || true

    PROJECT_DIR="$(pwd)"
    PARENT_DIR="$(dirname "$PROJECT_DIR")"
    BASE_NAME="$(basename "$PROJECT_DIR")"
    cd "$PARENT_DIR" || exit 0
    if [ -f /usr/local/bin/watchguard ]; then
        run_with_spinner "Removing /usr/local/bin/watchguard" sudo rm -f /usr/local/bin/watchguard || true
    elif [ -f /usr/bin/watchguard ]; then
        run_with_spinner "Removing /usr/bin/watchguard" sudo rm -f /usr/bin/watchguard || true
    fi
    run_with_spinner "Removing project directory" bash -c "rm -rf \"$BASE_NAME\"" || true
    echo -e "${GREEN}Project removed. Exiting installer.${NC}"
    exit 0
}

display_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
██╗    ██╗ █████╗ ████████╗ ██████╗██╗  ██╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ 
██║    ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
██║ █╗ ██║███████║   ██║   ██║     ███████║██║  ███╗██║   ██║███████║██████╔╝██║  ██║
██║███╗██║██╔══██║   ██║   ██║     ██╔══██║██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
╚███╔███╔╝██║  ██║   ██║   ╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
 ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 
EOF
    echo -e "${NC}"
}

check_watchguard_installed() {
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files | grep -q '^watchguard\.service'; then
            return 0
        fi
        if systemctl status watchguard >/dev/null 2>&1; then
            return 0
        fi
        if [ -f /etc/systemd/system/watchguard.service ] || [ -f /lib/systemd/system/watchguard.service ]; then
            return 0
        fi
    fi
    if [ -d /opt/watchguard ] || [ -d /usr/local/WatchGuard ]; then
        return 0
    fi
    return 1
}

display_info_box() {
    BOT_STATUS_C="${YELLOW}Not Installed${NC}"; BOT_STATUS_P="Not Installed"
    PANEL_STATUS_C="${YELLOW}Not Installed${NC}"; PANEL_STATUS_P="Not Installed"
    if command -v systemctl >/dev/null 2>&1; then
        SYSTEMD_UNITS=$(systemctl list-unit-files --type=service --no-legend --no-pager 2>/dev/null | awk '{print $1}')
    else
        SYSTEMD_UNITS=""
    fi
    PROCS=$(ps -eo command 2>/dev/null)

    if command -v systemctl >/dev/null 2>&1 && echo "$SYSTEMD_UNITS" | grep -q '^watchguard\.service'; then
        if systemctl is-active --quiet watchguard.service; then
            BOT_STATUS_C="${GREEN}Running${NC}"; BOT_STATUS_P="Running"
            PANEL_STATUS_C="${GREEN}Running${NC}"; PANEL_STATUS_P="Running"
        else
            BOT_STATUS_C="${YELLOW}Installed${NC}"; BOT_STATUS_P="Installed"
            PANEL_STATUS_C="${YELLOW}Installed${NC}"; PANEL_STATUS_P="Installed"
        fi
    else
        if command -v systemctl >/dev/null 2>&1 && echo "$SYSTEMD_UNITS" | grep -q '^watchguard-bot\.service'; then
            if systemctl is-active --quiet watchguard-bot.service; then
                BOT_STATUS_C="${GREEN}Running${NC}"; BOT_STATUS_P="Running"
            else
                BOT_STATUS_C="${YELLOW}Installed${NC}"; BOT_STATUS_P="Installed"
            fi
        elif echo "$PROCS" | grep -E "watchguard_service_bot\.py|watchguard_launcher\.py|watchguard_bot\.py" >/dev/null 2>&1; then
            BOT_STATUS_C="${GREEN}Running${NC}"; BOT_STATUS_P="Running"
        fi

        if command -v systemctl >/dev/null 2>&1 && echo "$SYSTEMD_UNITS" | grep -q '^watchguard-panel\.service'; then
            if systemctl is-active --quiet watchguard-panel.service; then
                PANEL_STATUS_C="${GREEN}Running${NC}"; PANEL_STATUS_P="Running"
            else
                PANEL_STATUS_C="${YELLOW}Installed${NC}"; PANEL_STATUS_P="Installed"
            fi
        elif echo "$PROCS" | grep -E "watchguard_service_panel\.py|watchguard_web_dashboard\.py" >/dev/null 2>&1; then
            PANEL_STATUS_C="${GREEN}Running${NC}"; PANEL_STATUS_P="Running"
        fi

        if echo "$PROCS" | grep -E "watchguard_service_suite\.py" >/dev/null 2>&1; then
            BOT_STATUS_C="${GREEN}Running${NC}"; BOT_STATUS_P="Running"
            PANEL_STATUS_C="${GREEN}Running${NC}"; PANEL_STATUS_P="Running"
        fi
    fi

    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(ip -4 addr show scope global 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)
    fi
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP="N/A"
    fi

    local width=68
    local title="WatchGuard"
    local subtitle="Installation Setup"
    local version_str
    if [ -n "$WATCHGUARD_VERSION" ]; then
        version_str="$WATCHGUARD_VERSION"
    elif [ -f "settings.json" ]; then
        version_str=$(python3 - << 'PYV' 2>/dev/null
import json
try:
    with open('settings.json','r',encoding='utf-8') as f:
        data=json.load(f)
        v=(data.get('version') or '').strip()
        print(v)
except Exception:
    print('')
PYV
        )
        [ -z "$version_str" ] && version_str="v1.0.0"
    else
        version_str="v1.0.0"
    fi
    local tel_handle="@AsanFillter"
    local tel_len=${#tel_handle}

    echo -e "${LGREEN}"
    printf "┌%s┐\n" "$(printf '─%.0s' $(seq 1 $width))"
    printf "│${LGREEN}%-${width}s${NC}${LGREEN}│\n" "$(printf '%*s' $(( (width + ${#title}) / 2)) "$title")"
    printf "│${LGREEN}%-${width}s${NC}${LGREEN}│\n" "$(printf '%*s' $(( (width + ${#subtitle}) / 2)) "$subtitle")"
    printf "│%-${width}s│\n" ""
    printf "│  ${LGREEN}• Version:${NC} %s${LGREEN}%-$(( width - 13 - ${#version_str} ))s│\n" "${B_MUSTARD}${version_str}${NC}" ""
    printf "│  ${LGREEN}• Server IP:${NC} %s${LGREEN}%-$(( width - 15 - ${#SERVER_IP} ))s│\n" "${CYAN}${SERVER_IP}${NC}" ""
    printf "│  ${LGREEN}• Bot Status:${NC} %s${LGREEN}%-$(( width - 13 - ${#BOT_STATUS_P} ))s│\n" "$BOT_STATUS_C" ""
    printf "│  ${LGREEN}• Panel Status:${NC} %s${LGREEN}%-$(( width - 15 - ${#PANEL_STATUS_P} ))s│\n" "$PANEL_STATUS_C" ""
    printf "│  ${LGREEN}• TelegramChannel:${NC} %s${LGREEN}%-$(( width - 22 - ${tel_len} ))s│\n" "${CYAN}${tel_handle}${NC}" ""
    printf "│%-${width}s│\n" ""
    printf "└%s┘\n" "$(printf '─%.0s' $(seq 1 $width))"
    echo -e "${NC}"
}

display_menu() {
    echo -e " ${CYAN}[1]${NC} ${CYAN}Install WatchGuard${NC}"
    echo -e " ${RED}[2]${NC} ${RED}Manage WatchGuard Services${NC}"
    echo -e " [3] Configure Bot (Token & Chat ID)"
    echo -e " [4] Configure Web Panel (Username & Password)"
    echo -e " [5] Update WatchGuard"
    echo -e " [6] Remove WatchGuard"
    echo -e " [7] Exit"
}

get_user_choice() {
    echo ""
    echo -e "──────────────────────────────────────────────"
    flush_stdin
    echo -ne "Please enter your choice [1-7]: "
    read -r choice
    if [[ ! "$choice" =~ ^[1-7]$ ]]; then
        echo -e "${RED}Invalid input! Please enter a number between 1 and 7.${NC}"
        echo ""
        flush_stdin
        show_reset_animation
        flush_stdin
        clear
        return 1
    fi
    return 0
}

handle_menu_selection() {
    case $choice in
        1)
            show_install_options
            ;;
        2)
            manage_watchguard
            ;;
        3)
            change_bot_token_chat_ids
            ;;
        4)
            change_web_panel_credentials
            ;;
        5)
            echo -e "${BOLD}${GREEN}Selected: [5] Update WatchGuard${NC}"
            REPO_OWNER="AsanFillter"
            REPO_NAME="WatchGuard"
            REPO_BRANCH="main"
            RAW_SETTINGS_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}/settings.json"
            ARCHIVE_URL="https://codeload.github.com/${REPO_OWNER}/${REPO_NAME}/tar.gz/refs/heads/${REPO_BRANCH}"

            LOCAL_VER=$(python3 - 2>/dev/null <<'PYV'
import json
try:
    with open('settings.json','r',encoding='utf-8') as f:
        d=json.load(f)
    v=(d.get('version') or '').strip()
    print(v if v else 'v0.0.0')
except Exception:
    print('v0.0.0')
PYV
            )

            REMOTE_VER=$(curl -fsSL "$RAW_SETTINGS_URL" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('version') or '').strip())" 2>/dev/null)

            if [ -z "$REMOTE_VER" ]; then
                echo -e "${YELLOW}Unable to fetch remote version. Skipping update.${NC}"
                break
            fi

            if [ "$LOCAL_VER" = "$REMOTE_VER" ]; then
                echo -e "${GREEN}Already up-to-date (version ${LOCAL_VER}).${NC}"
                break
            fi

            echo -e "${CYAN}Updating from ${LOCAL_VER} to ${REMOTE_VER}...${NC}"

            TMP_DIR=$(mktemp -d)
            TARBALL="$TMP_DIR/wg_update.tar.gz"
            if ! curl -fsSL -o "$TARBALL" "$ARCHIVE_URL"; then
                echo -e "${RED}Failed to download update archive.${NC}"
                rm -rf "$TMP_DIR"
                break
            fi
            if ! tar -xzf "$TARBALL" -C "$TMP_DIR"; then
                echo -e "${RED}Failed to extract update archive.${NC}"
                rm -rf "$TMP_DIR"
                break
            fi
            SRC_DIR=$(find "$TMP_DIR" -maxdepth 1 -type d -name "${REPO_NAME}-*" | head -n1)
            if [ -z "$SRC_DIR" ]; then
                echo -e "${RED}Update source directory not found.${NC}"
                rm -rf "$TMP_DIR"
                break
            fi

            PROTECT_FILES=(config.json auth_config.json settings.json labels.json servers.json domains.json .venv .git)

            if command -v rsync >/dev/null 2>&1; then
                RSYNC_EXCLUDES=()
                for f in "${PROTECT_FILES[@]}"; do
                    RSYNC_EXCLUDES+=(--exclude "$f")
                done
                run_with_spinner "Syncing updated files" rsync -a "$SRC_DIR"/ ./ "${RSYNC_EXCLUDES[@]}" || true
            else
                run_with_spinner "Copying updated files" bash -c '
set -e
SRC_DIR_REPL="$SRC_DIR"
for item in "$SRC_DIR_REPL"/*; do
  name=$(basename "$item")
  skip=0
  for ex in ${PROTECT_FILES[@]}; do
    if [ "$name" = "$ex" ]; then skip=1; break; fi
  done
  [ $skip -eq 1 ] && continue
  cp -R "$item" ./
done
' || true
            fi

            if [ -d .venv ]; then
                if [ -f .venv/bin/activate ]; then . .venv/bin/activate; elif [ -f .venv/Scripts/activate ]; then . .venv/Scripts/activate; fi
                run_with_spinner "Upgrading pip" bash -c "pip install --upgrade pip >/dev/null 2>&1" || true
                [ -f requirements.txt ] && run_with_spinner "Installing requirements" bash -c "pip install -r requirements.txt >/dev/null 2>&1" || true
            fi

            rm -rf "$TMP_DIR"
            echo -e "${GREEN}Update completed. Local configuration files preserved.${NC}"
            ;;
        6)
            uninstall_watchguard
            ;;
        7)
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice! Please enter a number between 1 and 7.${NC}"
            ;;
    esac
}

wait_for_continue() {
    echo ""
    echo -e "${CYAN}Press Enter to continue...${NC}"
    read -r
    clear
}

main() {
    while true; do
        display_banner
        display_info_box
        display_menu
        get_user_choice || continue
        handle_menu_selection
        if [ -z "$SKIP_WAIT" ]; then
            wait_for_continue
        else
            unset SKIP_WAIT
            clear
        fi
    done
}

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be run as root!${NC}"
    echo -e "${YELLOW}Please run it with sudo or as root user.${NC}"
    echo -e "${CYAN}Example: sudo ./install.sh${NC}"
    exit 1
fi

if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}This installer is designed for Linux systems only!${NC}"
    echo -e "${YELLOW}Current OS: $OSTYPE${NC}"
    exit 1
fi

main