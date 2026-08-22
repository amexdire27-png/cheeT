Option Explicit
' Launch the overflow tray with no console window.
Dim fso, sh, root, pythonw, venv
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root

venv = root & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(venv) Then
    pythonw = venv
Else
    pythonw = "pythonw.exe"
End If

sh.Run """" & pythonw & """ """ & root & "\tray_host.py""", 0, False
