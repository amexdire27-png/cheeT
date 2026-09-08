Option Explicit
' Launch the overflow tray with no console window.
Dim fso, sh, root, pythonw, venv, exe
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root
exe = root & "\cheeT1.exe"

If fso.FileExists(exe) Then
    sh.Run """" & exe & """ --tray", 0, False
    WScript.Quit 0
End If

venv = root & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(venv) Then
    pythonw = venv
Else
    pythonw = "pythonw.exe"
End If

If fso.FileExists(root & "\launch.py") Then
    sh.Run """" & pythonw & """ """ & root & "\launch.py"" --tray", 0, False
Else
    sh.Run """" & pythonw & """ """ & root & "\tray_host.py""", 0, False
End If
