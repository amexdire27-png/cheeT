Option Explicit
' Stop the background host, wait until it is gone, then start it again.
Dim fso, sh, wmi, procs, p, root, pythonw, venv, target, still, i, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root
target = LCase(root & "\main.py")

sh.Run "wscript.exe //B //Nologo """ & root & "\stop_host.vbs"" quiet", 0, True

On Error Resume Next
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
For i = 1 To 25
    still = False
    Set procs = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='pythonw.exe' OR Name='python.exe'")
    For Each p In procs
        cmd = LCase(p.CommandLine & "")
        If InStr(cmd, target) > 0 Then
            still = True
            Exit For
        End If
    Next
    If Not still Then Exit For
    WScript.Sleep 200
Next
On Error GoTo 0

' Give the singleton mutex a moment to drop after the last process dies.
WScript.Sleep 500

venv = root & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(venv) Then
    pythonw = venv
Else
    pythonw = "pythonw.exe"
End If

sh.Run """" & pythonw & """ """ & root & "\main.py""", 0, False
sh.Run "wscript.exe //B //Nologo """ & root & "\flash_status.vbs"" Restarted", 0, False
