# PageMind (Sync Host)

Invisible Windows copilot. Press a hotkey on a window (usually a browser). Google Gemini answers in a **Sync Host** toast, and **the same text is always copied to the clipboard** (`Ctrl+V`).

No console. No taskbar button. Overflow tray (`^`) icon: **Sync Host**.

---

## Apps you need to install

Only these. No Git, Visual Studio, Node, or extra runtimes.

| Need | App? | How |
|---|---|---|
| OS | Windows 10 or 11 | Already on the PC |
| Runtime | **Python 3.11+** | `setup.cmd` installs **Python 3.12** with winget if missing. Or install from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH** |
| API | **Gemini API key(s)** | Create keys in a browser at [Google AI Studio](https://aistudio.google.com/apikey) |

Optional: **App Installer / winget** (already on most Windows 11 PCs) so setup can install Python for you.

---

## Setup on a new PC

1. Copy this whole folder onto the PC. Any path is fine.
2. Get one or more Gemini keys: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
3. Double-click **`setup.cmd`**
4. If Notepad opens `config.json`, put keys in `"api_keys"`, save, then overflow **Sync Host → Start**
5. If keys were already in `config.json`, setup starts the host for you

That one script:

- Unblocks helper files
- Installs Python if needed
- Creates `.venv` and installs packages
- Creates `config.json` from the example if missing
- Registers the hidden logon tray icon
- Puts **Sync Host** on the desktop (**Stop** only)
- Starts the overflow icon, and the host if a real key is present

No admin. Safe to run again.

```powershell
cd <this-folder>
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`config.json` is gitignored. Do not commit live keys.

---

## Daily use

| Action | How |
|---|---|
| **Start** | Overflow `^` → **Sync Host** → **Start**, or Start hotkey |
| **Restart** | Overflow **Restart**, or Restart hotkey (stop then start) |
| **Stop** | Desktop **Sync Host** (tray stays so you can Start again) |
| **Picture** | Screenshot hotkey → Gemini |
| **Text** | Native text or screenshot OCR → Gemini |
| **Dismiss** | Close any Sync Host toast now |
| **Abort** | Cancel a request already sent / still analyzing |

Defaults (all changeable in `config.json`):

| What | Default |
|---|---|
| Picture | `Ctrl+Alt+P` |
| Text | `Ctrl+Alt+T` |
| Dismiss | `Ctrl+Alt+X` |
| Abort | `Ctrl+Alt+Z` |
| Start | `Ctrl+Alt+Shift+G` |
| Restart | `Ctrl+Alt+R` |

1. Focus the page.
2. Press Picture or Text.
3. Status toasts: **Sent** (2s), then **Analyzing…** if it is still working.
4. The answer toast appears. The **same text is on the clipboard** — paste with `Ctrl+V`.
5. Short answers (A, True, a letter) show as the toast title. Longer text shows as the toast body and is still copied.

Other toasts: **Started**, **Restarted**, **Stopped**, **Busy**, **Failed**, **Aborted**.

After logon, the **Sync Host** icon returns in the overflow. Start the host from there if it is not already running.

---

## Shortcuts — change in `config.json` only

The host, tray, and setup all read `hotkeys`. Use `Ctrl+Alt+P` or `ctrl + alt + p`. Save, then overflow **Restart**.

```json
"hotkeys": {
  "screenshot": "Ctrl+Alt+P",
  "ocr": "Ctrl+Alt+T",
  "dismiss": "Ctrl+Alt+X",
  "abort": "Ctrl+Alt+Z",
  "start": "Ctrl+Alt+Shift+G",
  "restart": "Ctrl+Alt+R"
}
```

| Config key | Default | What it does |
|---|---|---|
| `screenshot` | `Ctrl+Alt+P` | Picture / screenshot → Gemini |
| `ocr` | `Ctrl+Alt+T` | Text / OCR → Gemini |
| `dismiss` | `Ctrl+Alt+X` | Hide toasts now |
| `abort` | `Ctrl+Alt+Z` | Drop the in-flight Gemini call and unlock the host |
| `start` | `Ctrl+Alt+Shift+G` | Start the host (works even after desktop Stop) |
| `restart` | `Ctrl+Alt+R` | Stop, then start |

---

## API keys (list)

Put as many Gemini keys as you want. They are tried **in order** if one is rejected, rate-limited, or out of quota.

```json
"api_keys": [
  "first-key",
  "second-key",
  "third-key"
]
```

A single `"api_key"` / `"backup_api_key"` string still works and is merged into the list.

Env vars: `PAGEMIND_API_KEYS` (comma-separated), `PAGEMIND_API_KEY`, `PAGEMIND_BACKUP_API_KEY`.

---

## Other `config.json` settings

| Key | Meaning |
|---|---|
| `api_keys` | Gemini keys, tried in order |
| `model` | First model (`gemini-flash-lite-latest`) |
| `fallback_models` | Other models if the first 404s or fails |
| `api_base` | Gemini HTTP base URL |
| `system_prompt` | How Gemini answers |
| `notification_duration_seconds` | How long the **answer** toast stays (status toasts are 2s) |
| `request_timeout_seconds` | HTTP timeout per try |
| `screenshot_folder` | Saved PNGs (never auto-deleted) |
| `log_folder` | Rotating log file |

---

## Files

| File | Role |
|---|---|
| `setup.cmd` / `setup.ps1` | One-click new-PC setup |
| `config.json` | Keys + hotkeys (yours, gitignored) |
| `config.example.json` | Template |
| `install_startup.ps1` | Tray at logon + desktop Stop |
| `uninstall_startup.ps1` | Remove logon task, stop host/tray, delete desktop shortcut |
| `run_hidden.vbs` | Start the host with no window |
| `run_tray.vbs` | Start the overflow icon |
| `stop_host.vbs` | Stop the host only (desktop shortcut) |
| `restart_host.vbs` | Stop, then start |
| Desktop **Sync Host** | Stop |
| Overflow **Sync Host** | Start / Restart |

Logs: `%LOCALAPPDATA%\.cache\syshelper\logs\pagemind.log`  
Screenshots: `%LOCALAPPDATA%\.cache\syshelper\img\`

---

## Clear an existing setup

```powershell
cd <this-folder>
powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1
```

That stops the host, kills the tray, removes the logon task, and deletes the desktop shortcut.

Then optionally:

1. Delete `%LOCALAPPDATA%\.cache\syshelper\` (logs and screenshots)
2. Delete this folder (includes `.venv` and `config.json`)

To set it up again: copy the folder back and double-click **`setup.cmd`**.

---

## If something fails

| Problem | Fix |
|---|---|
| `python` not found | Run `setup.cmd` again, or install from python.org with **Add python.exe to PATH**, new window, setup again |
| winget / App Installer missing | Install Python yourself from python.org, then `setup.cmd` |
| Packages fail to install | Need internet. Then `setup.cmd` again |
| No toasts / hotkeys dead | Overflow **Start**. Check `api_keys` in `config.json` |
| Toast says **Busy** | Wait, or **Abort** (`Ctrl+Alt+Z`) |
| Gemini 503 / rate limit | Wait, or add more keys in `api_keys` |
| Need a clean stop | Desktop **Sync Host**, or `uninstall_startup.ps1` |
