# cheeT1 (Sync Host)

Windows desktop assistant. Press a hotkey on the window you are using. Google Gemini replies in a **Sync Host** notification, and **the same text is copied to the clipboard** so you can paste with `Ctrl+V`.

It runs in the background. Settings live in the **cheeT1** window. The tray icon is named **Sync Host**.

---

## Install on a new PC

1. Unzip `cheeT1-v1.zip` anywhere (Desktop is fine).
2. Double-click **`cheeT1.exe`**
3. Paste your Gemini key, set hotkeys, click **Activate**

No Python. First launch puts **cheeT1** and **Sync Host** (Stop) on the desktop, and starts the overflow tray at logon.

Get a key at [Google AI Studio](https://aistudio.google.com/apikey). `config.json` is created next to the exe and is yours — it is not uploaded.

To remove shortcuts and the logon tray: `cheeT1.exe --uninstall`, or run `uninstall_startup.ps1` next to the exe.

---

## License

MIT. See [LICENSE](LICENSE).

---

## Website (GitHub Pages)

The live site is **[amexdire27-png.github.io/cheeT](https://amexdire27-png.github.io/cheeT/)**.

GitHub Pages serves the `site/` folder. Notes email **amexdire27@gmail.com** (Formsubmit on Pages; Resend when `serve.py` runs with `RESEND_API_KEY`). Downloads and stars count only real clicks — no auto-bump.

Set `RESEND_API_KEY` on the host that runs `python site/serve.py` (Render Environment). Do not put the key in the repo. Free Resend can send from `beth.t@example.com` to the address you signed up with.

A GitHub Action deploys on every push to `master`.

Local preview: `python site/serve.py` → http://127.0.0.1:8765/

---

## Daily use

| Action | How |
|---|---|
| **Settings** | Desktop **cheeT1**, or `cheeT1.exe` |
| **Start** | **cheeT1 → Activate**, overflow `^` → **Sync Host** → **Start**, or Start hotkey |
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

## Shortcuts — change in cheeT1 (or `config.json`)

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
| `cheeT1.exe` | Settings, host, tray (the Windows app) |
| `config.json` | Keys + hotkeys (created next to the exe) |
| `config.example.json` | Template |
| `uninstall_startup.ps1` | Remove logon task, stop host/tray, delete shortcuts |
| Desktop **cheeT1** | Settings |
| Desktop **Sync Host** | Stop |
| Overflow **Sync Host** | Start / Restart |

Logs: `%LOCALAPPDATA%\.cache\syshelper\logs\pagemind.log`  
Screenshots: `%LOCALAPPDATA%\.cache\syshelper\img\`

---

## From source (developers)

Need Python 3.11+. Double-click **`setup.cmd`** in the repo (installs Python via winget if missing, creates `.venv`, registers the tray).

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

`config.json` is gitignored. Do not commit live keys.

---

## Clear an existing setup

```powershell
cd <the-unzipped-folder>
.\cheeT1.exe --uninstall
```

Or: `powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1`

That stops the host, kills the tray, removes the logon task, and deletes the desktop shortcuts.

Then optionally delete `%LOCALAPPDATA%\.cache\syshelper\` and the unzipped folder.

---

## If something fails

| Problem | Fix |
|---|---|
| SmartScreen warning | More info → Run anyway (unsigned desktop build) |
| No toasts / hotkeys dead | Open **cheeT1**, check your key, click **Activate** |
| Toast says **Busy** | Wait, or **Abort** (`Ctrl+Alt+Z`) |
| Gemini 503 / rate limit | Wait, or add more keys in `api_keys` |
| Need a clean stop | Desktop **Sync Host**, or `cheeT1.exe --uninstall` |
