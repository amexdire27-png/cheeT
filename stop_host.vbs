Option Explicit
' Silently stop the background host. No window, no prompt.
Dim fso, sh, wmi, procs, p, pidFile, pid, root, folder, cmd, target, quiet
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
root = LCase(folder)
target = root & "\main.py"
pidFile = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\.cache\syshelper\host.pid"
quiet = False
If WScript.Arguments.Count > 0 Then
    If LCase(Trim(WScript.Arguments(0))) = "quiet" Then quiet = True
End If

On Error Resume Next
If fso.FileExists(pidFile) Then
    pid = Trim(fso.OpenTextFile(pidFile, 1).ReadAll)
    If pid <> "" Then
        sh.Run "taskkill /F /T /PID " & pid, 0, True
    End If
    fso.DeleteFile pidFile, True
End If

Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='pythonw.exe' OR Name='python.exe'")
For Each p In procs
    cmd = LCase(p.CommandLine & "")
    If InStr(cmd, target) > 0 Then
        p.Terminate
    End If
Next
On Error GoTo 0

If Not quiet Then
    sh.Run "wscript.exe //B //Nologo """ & folder & "\flash_status.vbs"" Stopped", 0, False
End If
