# cheeT1 — features and tech stack

Windows on-screen assistant. You press a hotkey on the window you are using. Gemini answers in a **Sync Host** notification. The same text is copied to the clipboard so you can paste it.

This file is the product brief: what exists today, what it is built with, and how the desktop app is meant to be used.

---

## What it is

A small Windows app for people who want a fast answer from whatever is already on their screen — a doc, a tutorial, an error dialog, a spreadsheet, a browser tab — without opening a separate chat.

**cheeT1** is the settings window (version 1): your API key, your shortcuts, start and stop. **Sync Host** is the background service and tray icon that actually listens for those shortcuts.

No extra chat tab. You stay in the app you were already using.

---

## Features (now)

### Capture and ask

| Mode | What happens |
|---|---|
| **Picture** | Captures the active window and sends it to Gemini |
| **Text** | Reads accessible window text when it is available; otherwise uses the same capture path |

### Answers

- Gemini classifies what is on screen (short answer, code, true/false, or a longer / multiple-choice reply).
- A notification shows the useful part of the answer.
- **The same text is copied to the clipboard.** Paste with `Ctrl+V`.
- Status notifications: **Sent** (2s), **Analyzing…**, **Busy**, **Failed**, **Aborted**, plus **Started** / **Restarted** / **Stopped**.

### Control

| Action | How |
|---|---|
| Start | **cheeT1 → Activate**, overflow **Sync Host → Start**, or the Start hotkey |
| Restart | **Restart** in cheeT1 or the tray, or the Restart hotkey |
| Stop | Desktop **Sync Host** shortcut, or Stop in cheeT1 (the tray stays so you can start again) |
| Dismiss | Close the current notification |
| Abort | Cancel a request that is still running |

One service instance at a time. The tray process stays available after Stop so you can start again without reinstalling.

### Customize (cheeT1 version 1)

Open **cheeT1** (desktop shortcut, `cheeT1.cmd`, or after `setup.cmd`). First launch shows a short welcome, then settings.

- **API keys** — your own Gemini key(s). Extra keys are used if the first one is rejected, rate-limited, or out of quota.
- **Hotkeys** — click a shortcut, then press the keys you want.
- **Activate** — starts the background service. Stop / Restart from the same window.
- **Model** and how long the answer notification stays.
- Settings are stored in `config.json`. Save & apply reloads the service so changes take effect.

### Setup and lifecycle

- One-click **`setup.cmd`** on a new Windows 10/11 PC (installs Python via winget if needed, venv, packages, logon tray, desktop shortcuts).
- A standard user logon task brings the tray icon back after reboot.
- Captures are stored under `%LOCALAPPDATA%\.cache\syshelper\img\` (not auto-deleted).
- Logs: `%LOCALAPPDATA%\.cache\syshelper\logs\pagemind.log`.
- **`uninstall_startup.ps1`** removes the logon task, stops the service, and removes the desktop shortcuts.

### Default hotkeys

| Action | Default |
|---|---|
| Picture | `Ctrl+Alt+P` |
| Text | `Ctrl+Alt+T` |
| Dismiss | `Ctrl+Alt+X` |
| Abort | `Ctrl+Alt+Z` |
| Start | `Ctrl+Alt+Shift+G` |
| Restart | `Ctrl+Alt+R` |

---

## Tech stack

Python packaged as **`cheeT1.exe`** (settings, background host, and tray in one app). The settings window is tkinter. Capture uses mss, Pillow, and pywin32. Hotkeys use pynput. Notifications use Windows toasts. Gemini is called over HTTPS with the user’s own key.

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** (setup uses 3.12) | Win32, hotkeys, and HTTP in one project |
| Host | `main.py` + `pythonw` | Runs without a console window |
| Tray | `tray_host.py` + **pystray** | Overflow icon that stays after Stop |
| Hotkeys | **pynput** + custom `StrictHotKeys` | Global shortcuts; the last key of the combo must be pressed |
| Screen | **mss** + **Pillow** + **pywin32** | Window capture, JPEG for the API, PNG saved locally |
| Text | Win32 accessible text (`pywin32`) | Use real text when the window exposes it |
| AI | **Google Gemini** HTTP (`requests`) | `generativelanguage.googleapis.com` |
| Clipboard | **pyperclip** | Answer ready to paste |
| Notifications | Custom **Win32** layered windows (ctypes) | Short, timed toasts (2s / 5s) |
| Config | `config.json` (gitignored) | Keys, hotkeys, model, prompt |
| Autostart | **Task Scheduler** (`cheeT1.exe --tray`) | Tray at logon; start / stop / restart |
| Settings UI | **cheeT1** (`app.py` + `widgets.py`, plain **tkinter**) | Frameless window, drawn keycaps, status meter, sliding tabs — no widget toolkit |
| Install | `setup.cmd` / `setup.ps1` + **winget** | One double-click on a new PC |

**Python packages** (`requirements.txt`): `mss`, `pynput`, `pyperclip`, `requests`, `pywin32`, `Pillow`, `pystray`. The UI uses the standard library `tkinter`.

**Not used:** Electron, a public store listing.

---

## The desktop app (version 1)

**cheeT1** is the branded settings window. The engine behind it is the Sync Host service.

### Product

- First launch: welcome screen with the logo and **Version 1**.
- Settings: your Gemini API key(s), every hotkey, model, notification time.
- **Activate** starts the background service — same as other desktop utilities: tray icon, no console.
- People do not need to edit JSON unless they want to.

### UI

| Role | Color |
|---|---|
| Background | Black (`#0B0B0B`) |
| Primary actions / logo | Orange (`#FC6D0F`) |
| Text and borders | White (muted gray for secondary text) |

cheeT1 is the product name users see. Sync Host is the service name in the tray and on the Stop shortcut.

### Stack

Python service + a hand-drawn tkinter window. `app.py` writes `config.json` and uses the same start / stop / restart helpers as the tray. `widgets.py` holds the drawn parts: keycaps, status meter, ticked slider, popup dropdown, sliding tab underline.

Later options: a one-file installer, or other model providers.

---

## Not in version 1

- One-file installer / Start Menu entry
- Providers other than Gemini in the UI
- macOS / Linux
- Accounts or a store listing
