#!/usr/bin/env bash
# Hire Journey — one-command setup and runner.
#
#   ./script.sh            set everything up (first run) and start the app
#   ./script.sh start      same as above
#   ./script.sh stop       stop backend + frontend (database keeps running)
#   ./script.sh stop --db  also stop the Postgres container
#   ./script.sh status     show what is running
#   ./script.sh logs       follow backend + frontend logs
#   ./script.sh test       run backend (pytest) and frontend (vitest) tests
#   ./script.sh reset-db   DESTROY the database container and its data
#   ./script.sh help

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
RUN_DIR="$ROOT/.run"
VENV="$BACKEND/.venv"

DB_CONTAINER="${DB_CONTAINER:-career-engine-db}"
DB_NAME="${DB_NAME:-career_engine}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_PORT="${DB_PORT:-5432}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# ---------- output helpers ----------
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; BLUE=$'\033[34m'; RESET=$'\033[0m'
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; BLUE=""; RESET=""
fi
step() { echo; echo "${BOLD}${BLUE}==>${RESET} ${BOLD}$*${RESET}"; }
ok()   { echo "  ${GREEN}✔${RESET} $*"; }
warn() { echo "  ${YELLOW}!${RESET} $*"; }
die()  { echo "${RED}✖ $*${RESET}" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

trap 'echo "${RED}✖ Failed at line $LINENO. See messages above.${RESET}" >&2' ERR

# ---------- helpers ----------
port_in_use() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

pid_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

hash_file() {
  if have shasum; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi
}

wait_for_url() { # url, label, timeout_seconds
  local url="$1" label="$2" timeout="${3:-90}" i=0
  until curl -fsS -o /dev/null "$url" 2>/dev/null; do
    i=$((i + 1))
    if (( i > timeout )); then
      die "$label did not become ready within ${timeout}s. Check logs in $RUN_DIR/"
    fi
    sleep 1
  done
}

set_env_value() { # file, key, value (replaces the line KEY=... in place)
  local file="$1" key="$2" value="$3"
  python3 - "$file" "$key" "$value" <<'PY'
import sys, re
path, key, value = sys.argv[1:4]
text = open(path).read()
pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
line = f"{key}={value}"
text = pattern.sub(lambda _m: line, text) if pattern.search(text) else text.rstrip("\n") + "\n" + line + "\n"
open(path, "w").write(text)
PY
}

get_env_value() { # file, key
  grep -E "^$2=" "$1" 2>/dev/null | tail -n1 | cut -d= -f2- || true
}

# ---------- steps ----------
check_prereqs() {
  step "Checking prerequisites"
  have docker  || die "Docker is required (https://www.docker.com/products/docker-desktop)."
  have node    || die "Node.js 20+ is required (https://nodejs.org)."
  have npm     || die "npm is required (comes with Node.js)."
  have curl    || die "curl is required."
  have python3 || die "python3 is required."
  have lsof    || die "lsof is required."

  local node_major
  node_major="$(node -p 'process.versions.node.split(".")[0]')"
  (( node_major >= 20 )) || die "Node.js 20+ required (found $(node --version))."
  ok "Node $(node --version), npm $(npm --version)"

  if ! docker info >/dev/null 2>&1; then
    if [[ "$(uname)" == "Darwin" ]] && [[ -d "/Applications/Docker.app" ]]; then
      warn "Docker engine is not running — starting Docker Desktop..."
      open -a Docker
      local i=0
      until docker info >/dev/null 2>&1; do
        i=$((i + 1)); (( i > 120 )) && die "Docker did not start in time. Start it manually and re-run."
        sleep 1
      done
    else
      die "Docker engine is not running. Start Docker and re-run."
    fi
  fi
  ok "Docker engine is running"
}

start_database() {
  step "Starting PostgreSQL ($DB_CONTAINER)"
  if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    ok "Container already running"
  elif docker ps -a --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    docker start "$DB_CONTAINER" >/dev/null
    ok "Existing container started"
  else
    if port_in_use "$DB_PORT"; then
      local requested="$DB_PORT"
      while port_in_use "$DB_PORT"; do DB_PORT=$((DB_PORT + 1)); done
      warn "Port $requested is used by another process (e.g. a local Postgres); using $DB_PORT for the container"
    fi
    docker run -d \
      --name "$DB_CONTAINER" \
      -e POSTGRES_USER="$DB_USER" \
      -e POSTGRES_PASSWORD="$DB_PASSWORD" \
      -e POSTGRES_DB="$DB_NAME" \
      -p "$DB_PORT":5432 \
      postgres:16 >/dev/null
    ok "Container created"
  fi

  local i=0
  until docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
    i=$((i + 1)); (( i > 60 )) && die "PostgreSQL did not become ready in 60s."
    sleep 1
  done
  local real_port
  real_port="$(docker port "$DB_CONTAINER" 5432/tcp 2>/dev/null | head -n1 | sed 's/.*://' || true)"
  [[ -n "$real_port" ]] && DB_PORT="$real_port"
  ok "PostgreSQL is accepting connections on localhost:$DB_PORT"
}

setup_env() {
  step "Configuring environment files"
  if [[ ! -f "$BACKEND/.env" ]]; then
    cp "$BACKEND/.env.example" "$BACKEND/.env"
    ok "Created backend/.env"
  else
    ok "backend/.env exists (left untouched)"
  fi
  if [[ ! -f "$FRONTEND/.env" ]]; then
    cp "$FRONTEND/.env.example" "$FRONTEND/.env"
    ok "Created frontend/.env"
  else
    ok "frontend/.env exists (left untouched)"
  fi

  # Generate a real JWT secret if the placeholder is still there.
  local secret
  secret="$(get_env_value "$BACKEND/.env" SECRET_KEY)"
  if [[ -z "$secret" || "$secret" == "change-this-to-a-random-secret-key" ]]; then
    set_env_value "$BACKEND/.env" SECRET_KEY "$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    ok "Generated SECRET_KEY"
  fi

  # Point DATABASE_URL at the port the container is really published on.
  local real_port
  real_port="$(docker port "$DB_CONTAINER" 5432/tcp 2>/dev/null | head -n1 | sed 's/.*://' || true)"
  [[ -n "$real_port" ]] && DB_PORT="$real_port"
  local expected_url="postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"
  local current_url
  current_url="$(get_env_value "$BACKEND/.env" DATABASE_URL)"
  if [[ -z "$current_url" ]]; then
    set_env_value "$BACKEND/.env" DATABASE_URL "$expected_url"
  elif [[ "$current_url" =~ ^postgresql\+asyncpg://[^@]+@(localhost|127\.0\.0\.1):[0-9]+/"$DB_NAME"$ && "$current_url" != "$expected_url" ]]; then
    set_env_value "$BACKEND/.env" DATABASE_URL "$expected_url"
    ok "DATABASE_URL updated to use port $DB_PORT"
  fi

  # Resume extraction needs at least one LLM key. The app still runs without one.
  if [[ -z "$(get_env_value "$BACKEND/.env" GROQ_API_KEY)" \
     && -z "$(get_env_value "$BACKEND/.env" GEMINI_API_KEY)" \
     && -z "$(get_env_value "$BACKEND/.env" OPENAI_API_KEY)" ]]; then
    if [[ -n "${GROQ_API_KEY:-}" ]]; then
      set_env_value "$BACKEND/.env" GROQ_API_KEY "$GROQ_API_KEY"; ok "GROQ_API_KEY taken from your shell"
    elif [[ -n "${GEMINI_API_KEY:-}" ]]; then
      set_env_value "$BACKEND/.env" GEMINI_API_KEY "$GEMINI_API_KEY"; ok "GEMINI_API_KEY taken from your shell"
    elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
      set_env_value "$BACKEND/.env" OPENAI_API_KEY "$OPENAI_API_KEY"; ok "OPENAI_API_KEY taken from your shell"
    else
      warn "No LLM API key set. The app will run, but resume upload returns 503."
      warn "Add GROQ_API_KEY (free: https://console.groq.com/keys) to backend/.env, then re-run."
    fi
  fi
}

# Find an interpreter in the supported range (3.11 - 3.13).
find_python() {
  local c v
  for c in python3.13 python3.12 python3.11 python3; do
    if have "$c"; then
      v="$("$c" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
      case "$v" in 3.11|3.12|3.13) echo "$c"; return 0 ;; esac
    fi
  done
  return 1
}

setup_backend() {
  step "Setting up backend (Python virtualenv + dependencies)"

  if [[ -x "$VENV/bin/python" ]]; then
    local vv
    vv="$("$VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    case "$vv" in
      3.11|3.12|3.13) ok "Using existing virtualenv (Python $vv)" ;;
      *) warn "Existing virtualenv uses unsupported Python $vv — recreating"; rm -rf "$VENV" ;;
    esac
  fi

  if [[ ! -x "$VENV/bin/python" ]]; then
    local py
    if py="$(find_python)"; then
      "$py" -m venv "$VENV"
      ok "Created virtualenv with $py"
    elif have uv; then
      warn "No Python 3.11-3.13 found; asking uv to provide 3.13"
      uv venv --python 3.13 "$VENV"
      ok "Created virtualenv with uv (Python 3.13)"
    else
      die "Python 3.11-3.13 is required (3.14 is NOT supported; found $(python3 --version 2>&1)).
  Install one, e.g.  brew install python@3.13   (or install uv: https://docs.astral.sh/uv/)"
    fi
  fi

  local req_hash stamp="$VENV/.requirements.sha256"
  req_hash="$(hash_file "$BACKEND/requirements-dev.txt")-$(hash_file "$BACKEND/requirements.txt")"
  if [[ -f "$stamp" && "$(cat "$stamp")" == "$req_hash" ]]; then
    ok "Python dependencies up to date"
  else
    echo "  Installing Python dependencies (first run takes a few minutes)..."
    if [[ -x "$VENV/bin/pip" ]]; then
      "$VENV/bin/pip" install --quiet --upgrade pip
      "$VENV/bin/pip" install --quiet -r "$BACKEND/requirements-dev.txt"
    else
      uv pip install --quiet --python "$VENV/bin/python" -r "$BACKEND/requirements-dev.txt"
    fi
    echo "$req_hash" > "$stamp"
    ok "Python dependencies installed"
  fi
}

setup_frontend() {
  step "Setting up frontend (npm dependencies)"
  local lock_hash stamp="$FRONTEND/node_modules/.package-lock.sha256"
  lock_hash="$(hash_file "$FRONTEND/package-lock.json")"
  if [[ -d "$FRONTEND/node_modules" && -f "$stamp" && "$(cat "$stamp")" == "$lock_hash" ]]; then
    ok "npm dependencies up to date"
  else
    echo "  Installing npm dependencies..."
    (cd "$FRONTEND" && npm ci --no-audit --no-fund --loglevel=error)
    echo "$lock_hash" > "$stamp"
    ok "npm dependencies installed"
  fi
}

run_migrations() {
  step "Applying database migrations"
  (cd "$BACKEND" && "$VENV/bin/alembic" upgrade head)
  ok "Database schema is at head"
}

start_services() {
  step "Starting services"
  mkdir -p "$RUN_DIR"

  if pid_alive "$RUN_DIR/backend.pid"; then
    ok "Backend already running (pid $(cat "$RUN_DIR/backend.pid"))"
  else
    port_in_use "$BACKEND_PORT" && die "Port $BACKEND_PORT is already in use. Free it or set BACKEND_PORT=<port>."
    (cd "$BACKEND" && nohup "$VENV/bin/uvicorn" app.main:app --reload \
      --host 127.0.0.1 --port "$BACKEND_PORT" >"$RUN_DIR/backend.log" 2>&1 &
     echo $! >"$RUN_DIR/backend.pid")
    ok "Backend starting (log: .run/backend.log)"
  fi

  if pid_alive "$RUN_DIR/frontend.pid"; then
    ok "Frontend already running (pid $(cat "$RUN_DIR/frontend.pid"))"
  else
    port_in_use "$FRONTEND_PORT" && die "Port $FRONTEND_PORT is already in use. Free it or set FRONTEND_PORT=<port>."
    (cd "$FRONTEND" && nohup npm run dev -- --port "$FRONTEND_PORT" >"$RUN_DIR/frontend.log" 2>&1 &
     echo $! >"$RUN_DIR/frontend.pid")
    ok "Frontend starting (log: .run/frontend.log)"
  fi

  echo "  Waiting for services to become ready..."
  wait_for_url "http://127.0.0.1:$BACKEND_PORT/health" "Backend" 90
  ok "Backend is healthy"
  wait_for_url "http://127.0.0.1:$FRONTEND_PORT/login" "Frontend" 120
  ok "Frontend is ready"
}

print_summary() {
  echo
  echo "${BOLD}${GREEN}Hire Journey is up and running 🚀${RESET}"
  echo
  echo "  App         http://localhost:$FRONTEND_PORT"
  echo "  API         http://localhost:$BACKEND_PORT"
  echo "  API docs    http://localhost:$BACKEND_PORT/docs"
  echo "  Database    postgresql://$DB_USER:****@localhost:$DB_PORT/$DB_NAME"
  echo "  Logs        $RUN_DIR/{backend,frontend}.log   (./script.sh logs)"
  echo
  echo "  Stop with   ./script.sh stop     (Ctrl+C below also stops everything)"
}

stop_pidfile() { # name
  local f="$RUN_DIR/$1.pid"
  if pid_alive "$f"; then
    local pid; pid="$(cat "$f")"
    # Kill the whole process tree (uvicorn reloader / next dev children).
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
    ok "Stopped $1 (pid $pid)"
  else
    ok "$1 not running"
  fi
  rm -f "$f"
}

cmd_stop() {
  step "Stopping services"
  stop_pidfile backend
  stop_pidfile frontend
  # Catch orphaned children bound to our ports.
  for p in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    local pids; pids="$(lsof -nP -tiTCP:"$p" -sTCP:LISTEN 2>/dev/null || true)"
    [[ -n "$pids" ]] && kill $pids 2>/dev/null || true
  done
  if [[ "${1:-}" == "--db" ]]; then
    docker stop "$DB_CONTAINER" >/dev/null 2>&1 && ok "Stopped database container" || ok "Database container not running"
  fi
}

cmd_status() {
  step "Status"
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$DB_CONTAINER"; then ok "Database   running"; else warn "Database   stopped"; fi
  if pid_alive "$RUN_DIR/backend.pid"; then ok "Backend    running  http://localhost:$BACKEND_PORT"; else warn "Backend    stopped"; fi
  if pid_alive "$RUN_DIR/frontend.pid"; then ok "Frontend   running  http://localhost:$FRONTEND_PORT"; else warn "Frontend   stopped"; fi
}

cmd_logs() {
  mkdir -p "$RUN_DIR"; touch "$RUN_DIR/backend.log" "$RUN_DIR/frontend.log"
  tail -n 50 -f "$RUN_DIR/backend.log" "$RUN_DIR/frontend.log"
}

cmd_test() {
  check_prereqs
  setup_env
  setup_backend
  setup_frontend
  step "Backend tests (pytest)"
  (cd "$BACKEND" && "$VENV/bin/pytest" -q)
  step "Frontend tests (vitest)"
  (cd "$FRONTEND" && npm test --silent)
  echo; ok "All tests passed"
}

cmd_reset_db() {
  read -r -p "This DELETES the '$DB_CONTAINER' container and all its data. Type 'yes' to continue: " answer
  [[ "$answer" == "yes" ]] || die "Aborted."
  docker rm -f "$DB_CONTAINER" >/dev/null 2>&1 || true
  ok "Database container removed. Run ./script.sh to recreate it."
}

cmd_start() {
  check_prereqs
  start_database
  setup_env
  setup_backend
  setup_frontend
  run_migrations
  start_services
  print_summary

  # Foreground mode: Ctrl+C shuts the app down cleanly. If the terminal is not
  # interactive (CI, piped), return immediately and leave services running.
  if [[ -t 1 ]]; then
    trap 'echo; cmd_stop; exit 0' INT TERM
    echo
    echo "  Press Ctrl+C to stop. Streaming logs:"
    echo
    tail -n 0 -f "$RUN_DIR/backend.log" "$RUN_DIR/frontend.log" &
    wait $!
  fi
}

usage() {
  sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

case "${1:-start}" in
  start)    cmd_start ;;
  stop)     shift || true; cmd_stop "${1:-}" ;;
  status)   cmd_status ;;
  logs)     cmd_logs ;;
  test)     cmd_test ;;
  reset-db) cmd_reset_db ;;
  help|-h|--help) usage ;;
  *) usage; exit 1 ;;
esac
