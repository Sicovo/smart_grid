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