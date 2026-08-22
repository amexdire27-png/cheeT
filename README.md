# PageMind

Invisible Windows copilot. Press a hotkey on any window — usually a browser — and a 5-second toast returns the answer from Google Gemini. No console, no tray icon, no taskbar button.

| Hotkey | Mode |
|---|---|
| `Ctrl+Alt+P` | Picture — screenshot the active window and ask Gemini |
| `Ctrl+Alt+T` | Text — native text or screenshot OCR, then ask Gemini |
| `Ctrl+Alt+X` | Dismiss — force-close any Sync Host toast immediately |
| `Ctrl+Alt+Shift+G` | Start — start the host (same as overflow Start) |
| `Ctrl+Alt+R` | Restart — stop then start the host (same as overflow Restart) |

Long answers are no longer copied by character count. Gemini classifies the page first:

| Page type | What you get |
|---|---|
| Short-answer (fill-in, one word, number, formula) | Full answer on the clipboard. Native toast: “Answer arrived”. |
| Write-a-code | Full code on the clipboard. Same “arrived” toast. |
| Both short-answer and code | Combined paste-ready solution on the clipboard. Same toast. |
| True / False (or Yes / No) | `True` or `False` in a native Windows notification. |
| Anything else (MCQ, explain, article, error…) | The answer in a native Windows notification. |

## Requirements

- Windows 10/11
- Python 3.11 or newer (install from python.org and enable **Add python.exe to PATH**)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

```powershell
cd C:\Users\Gr_14\Documents\Fluffy
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy config.example.json config.json
```

Open `config.json` and set `api_key`. Optionally set `backup_api_key` — PageMind switches to it if the first key is rejected or runs out of quota. You can also set `PAGEMIND_API_KEY` / `PAGEMIND_BACKUP_API_KEY` instead.

`config.json` is gitignored. Do not commit a live key.

If an API key was pasted into chat or a ticket, rotate it in AI Studio and put the new value only in `config.json`.

## Run in the background

Silent (no console):

```powershell
wscript .\run_hidden.vbs
```

Or:

```powershell
pythonw .\main.py
```

Use `python .\main.py` only while debugging. Set `PAGEMIND_DEBUG=1` if you want the console to stay visible. Otherwise PageMind hides it as soon as it starts.

A second instance exits immediately. Logs go to:

`%LOCALAPPDATA%\.cache\syshelper\logs\pagemind.log`

Screenshots go to:

`%LOCALAPPDATA%\.cache\syshelper\img\`

Those folders are created on first run and marked hidden. Nothing is deleted from `img`.

## Start automatically with Windows

Recommended — a hidden logon task (no admin):

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
```

Remove it with:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1
```

Alternative — Startup folder:

1. Press `Win+R`, type `shell:startup`, press Enter.
2. Create a shortcut to `run_hidden.vbs` in that folder.

If toasts say Gemini is temporarily unavailable (`HTTP 503`), wait a few seconds and retry, or set `"model"` in `config.json` to `gemini-2.0-flash`.

## Using it

1. Focus the page or app you care about.
2. Press `Ctrl+Alt+P` (picture / screenshot) or `Ctrl+Alt+T` (text / OCR).
3. A native Windows notification appears (same style as other local toasts).
4. True/False and other glanceable answers show in that notification.
5. Short-answer and code questions copy to the clipboard; the toast only says the answer arrived — paste with `Ctrl+V`.

## Configuration

All of this lives in `config.json`:

| Key | Meaning |
|---|---|
| `api_key` | Gemini API key |
| `backup_api_key` | Second Gemini key used when the first is rejected or out of quota |
| `model` | Default `gemini-flash-latest` |
| `hotkeys.screenshot` / `hotkeys.ocr` / `hotkeys.dismiss` / `hotkeys.start` / `hotkeys.restart` | pynput-style hotkeys |
| `system_prompt` | How Gemini answers |
| `notification_duration_seconds` | Toast lifetime (short ≈ 5 seconds) |
| `screenshot_folder` | Permanent PNG storage |
| `log_folder` | Rotating log file |
| `request_timeout_seconds` | HTTP timeout |

## Package as a single .exe

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name PageMind `
  --hidden-import=pynput.keyboard._win32 `
  --hidden-import=pynput.mouse._win32 `
  --hidden-import=win32timezone `
  --hidden-import=windows_toasts `
  --hidden-import=winotify `
  main.py
```

Copy `config.json` next to `dist\PageMind.exe`. Point the logon task at the exe instead of `pythonw`.

## Stop it

Task Manager → `pythonw.exe` (or `PageMind.exe`) → End task.

If you used the installer:

```powershell
Stop-ScheduledTask -TaskName PageMind
```
