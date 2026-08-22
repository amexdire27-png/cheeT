# PageMind (Sync Host)

Invisible Windows copilot. Press a hotkey on a window (usually a browser). Google Gemini answers in a toast, and **the same text is copied to the clipboard** (`Ctrl+V`).

No console. No taskbar button. Overflow tray icon: **Sync Host**.

---

## Apps you need to install

You only need these. Nothing else (no Git, no Visual Studio, no extra runtimes).

| App | Why | How |
|---|---|---|
| **Windows 10 or 11** | This tool is Windows-only | Already on the PC |
| **Python 3.11 or newer** | Runs the host and tray | `setup.cmd` installs **Python 3.12** with winget if it is missing. Or install yourself from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH** |
| **A Gemini API key** | Talks to Google Gemini | Create a key at [Google AI Studio](https://aistudio.google.com/apikey) (browser). Not an installed app |

Optional: **App Installer / winget** (already on most Windows 11 PCs) so setup can install Python for you.

Do **not** install: Git, Node, Visual C++ Build Tools, Chrome (any browser is fine).

---

## Setup on a new PC (easy)

1. Copy this whole folder onto the PC (USB, zip, whatever). Any path is fine.
2. Get a Gemini API key: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
3. Double-click **`setup.cmd`**
4. If `config.json` opens in Notepad, paste the key into `"api_key"` and save. Then overflow **Sync Host → Start**.
5. If the key was already in `config.json`, setup starts the host for you.

That one script:

- Unblocks the helper files
- Installs Python if needed
- Creates `.venv` and installs packages
- Creates `config.json` from the example if missing
- Registers the hidden logon tray icon
- Puts **Sync Host** on the desktop (this **stops** the host)
- Starts the overflow icon (and the host if a real key is present)

No admin. Run it again any time; it is safe to repeat.

PowerShell instead of double-click:

```powershell
cd <this-folder>
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`config.json` is gitignored. Do not commit a live key.

---

## Daily use

| Action | How |
|---|---|
| Start | Overflow `^` → **Sync Host** → **Start**, or the Start hotkey |
| Restart | Overflow **Restart**, or the Restart hotkey |
| Stop | Desktop **Sync Host** shortcut (tray icon stays so you can Start again) |
| Picture | Screenshot hotkey (default `Ctrl+Alt+P`) |
| Text | OCR / text hotkey (default `Ctrl+Alt+T`) |
| Dismiss toast | Dismiss hotkey (default `Ctrl+Alt+X`) |

1. Focus the page.
2. Press Picture or Text.
3. Read the toast, or paste with `Ctrl+V` (clipboard always matches the toast).

After logon, the **Sync Host** icon comes back in the overflow. Start the host from there (or setup already started it this session).

---

## Shortcuts (`config.json`)

All hotkeys are only in `config.json` → `hotkeys`. The host, tray, and setup read that file.

```json
"hotkeys": {
  "screenshot": "Ctrl+Alt+P",
  "ocr": "Ctrl+Alt+T",
  "dismiss": "Ctrl+Alt+X",
  "start": "Ctrl+Alt+Shift+G",
  "restart": "Ctrl+Alt+R"
}
```

`Ctrl+Alt+P` or `ctrl + alt + p` both work. Change what you want; the rest keep defaults. Save, then overflow **Restart**.

| Key in config | Default | What it does |
|---|---|---|
| `screenshot` | `Ctrl+Alt+P` | Picture / screenshot → Gemini |
| `ocr` | `Ctrl+Alt+T` | Text / OCR → Gemini |
| `dismiss` | `Ctrl+Alt+X` | Close any Sync Host toast now |
| `start` | `Ctrl+Alt+Shift+G` | Start the host |
| `restart` | `Ctrl+Alt+R` | Stop, then start |

---

## Other `config.json` settings

| Key | Meaning |
|---|---|
| `api_key` | Gemini API key |
| `backup_api_key` | Used if the first key is rejected or out of quota |
| `model` | Default `gemini-flash-lite-latest` |
| `fallback_models` | Tried if the main model fails |
| `system_prompt` | How Gemini answers |
| `notification_duration_seconds` | How long the answer toast stays |
| `request_timeout_seconds` | HTTP timeout |
| `screenshot_folder` | Saved PNGs (never auto-deleted) |
| `log_folder` | Rotating log file |

You can set `PAGEMIND_API_KEY` / `PAGEMIND_BACKUP_API_KEY` instead of putting keys in the file.

---

## Files that matter

| File | Role |
|---|---|
| `setup.cmd` | Double-click setup on a new PC |
| `config.json` | Your key and hotkeys (created on first setup) |
| `install_startup.ps1` | Tray at logon + desktop Stop shortcut |
| `uninstall_startup.ps1` | Removes the logon task and stops tray/host |
| Desktop **Sync Host** | Stops the host only |
| Overflow **Sync Host** | Start / Restart |

Logs: `%LOCALAPPDATA%\.cache\syshelper\logs\pagemind.log`  
Screenshots: `%LOCALAPPDATA%\.cache\syshelper\img\`

---

## If something fails

| Problem | Fix |
|---|---|
| `python` not found | Run `setup.cmd` again, or install from python.org with **Add python.exe to PATH**, new window, setup again |
| winget / App Installer missing | Install Python yourself from python.org, then `setup.cmd` |
| Packages fail to install | Need internet. Then `setup.cmd` again |
| No toasts / hotkeys dead | Overflow **Start**. Check `api_key` in `config.json` |
| Gemini 503 | Wait a few seconds and retry |
| Need a clean stop | Desktop **Sync Host**, or `uninstall_startup.ps1` |

---

## Uninstall autostart

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1
```

Then delete this folder if you want it gone.
