Option Explicit
' Show a 2s Started / Restarted / Stopped toast with no window.
Dim fso, sh, root, pythonw, venv, title
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root

title = "Started"
If WScript.Arguments.Count > 0 Then
    title = Trim(WScript.Arguments(0))
End If

venv = root & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(venv) Then
    pythonw = venv
Else
    pythonw = "pythonw.exe"
End If

sh.Run """" & pythonw & """ """ & root & "\status_toast.py"" " & title, 0, False
