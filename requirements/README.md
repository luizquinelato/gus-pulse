# Requirements Structure

This directory contains centralized dependency management for the Pulse Platform **Python services**.

> **Note**: Frontend services (Node.js/React) use `package.json` managed via npm.

## 📁 Files

- **`install.txt`** — Orchestrator: lists every requirements file and package.json in the project. Read by `scripts/setup_envs.py`.
- **`root.txt`** — Root-level packages for standalone scripts in `/scripts` (runs in project-root `.venv`).
- `services/backend/requirements/install.txt` — Backend service dependencies (managed inside the service).
- `services/auth/requirements/install.txt` — Auth service dependencies (managed inside the service).

## 🚀 Installation

### Complete Setup (Recommended)

```bash
# Creates all virtual environments + installs all dependencies in one pass
python scripts/setup_envs.py
```

This handles:
- Root `.venv` with packages from `requirements/root.txt`
- `services/backend/.venv` with packages from `services/backend/requirements/install.txt`
- `services/auth/.venv` with packages from `services/auth/requirements/install.txt`
- `npm install` for `services/frontend` and `services/frontend-etl`

### Force Reinstall

```bash
python scripts/setup_envs.py --force
```

## 📦 Dependency Locations

| Scope | File | Venv |
|---|---|---|
| Standalone scripts | `requirements/root.txt` | `.venv/` (project root) |
| Backend service | `services/backend/requirements/install.txt` | `services/backend/.venv/` |
| Auth service | `services/auth/requirements/install.txt` | `services/auth/.venv/` |
| Frontend | `services/frontend/package.json` | `services/frontend/node_modules/` |
| Frontend ETL | `services/frontend-etl/package.json` | `services/frontend-etl/node_modules/` |

## 🛠️ One-Time Developer Tools

Install globally when needed — **not** inside any venv.

| Tool | Install | Purpose |
|---|---|---|
| `git-filter-repo` | `pip install git-filter-repo` | Rewrite / purge files from git history |

## 🔧 Adding New Dependencies

1. **Root script dependency**: add to `requirements/root.txt`
2. **Backend dependency**: add to `services/backend/requirements/install.txt`
3. **Auth dependency**: add to `services/auth/requirements/install.txt`
4. **Reinstall**: run `python scripts/setup_envs.py --force`
