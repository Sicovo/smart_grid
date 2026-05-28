# Smart Grid Dashboard

# Requirements

- Python 3.10+
- Node 22+
- npm

## Setup

```bash
./setup.sh

./run_backend.sh
./run_poller.sh
./run_frontend.sh
```

On Windows, start both frontend and backend with one command:

```powershell
.\run_windows.ps1
```

To start frontend, backend, and the poller together:

```powershell
.\run_windows_all.ps1
```

## Module telemetry ingestion

The poller now collects grid demand data from the external simulation source and can also poll individual Pico firmware boards for telemetry.

Set board URLs with environment variables before running `backend/poller.py`:

```bash
PICO_PV_URL=http://192.168.4.2:80 \
PICO_GRID_URL=http://192.168.4.3:80 \
PICO_EXPORT_URL=http://192.168.4.4:80 \
PICO_CAP_URL=http://192.168.4.5:80 \
PICO_LED_URL=http://192.168.4.6:80 \
python backend/poller.py
```

The poller fetches `/tlm` from each configured board and stores the telemetry in the `module_snapshots` table via `save_module_snapshot()`.

Board telemetry can also still be sent manually to the backend via `/smps/ingest`.

## Access Over Wi-Fi

The frontend dev server listens on your computer's LAN address, and the frontend calls the backend on the same host by default.

1. Start the backend and frontend from this repo.
2. Find your computer's Wi-Fi IPv4 address.
3. Open `http://<your-ip>:5173` from another device on the same network.

Example:

```text
http://192.168.1.42:5173
```

If your backend runs on a different machine or port, set `VITE_API_BASE_URL` before starting the frontend.

```bash
VITE_API_BASE_URL=http://192.168.1.50:8000 npm run dev
```