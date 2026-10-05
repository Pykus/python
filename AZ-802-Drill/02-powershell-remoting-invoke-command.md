# AZ-802 Drill 02 — PowerShell Remoting and Invoke-Command

## Core idea

On Windows, PowerShell Remoting normally uses **WinRM / WS-Management**.

Typical flow:

```text
ADMIN-PC
   |
   | WinRM / PowerShell Remoting
   | TCP 5985 (HTTP) or 5986 (HTTPS)
   v
SERVER01
```

Use:

- `Enter-PSSession` for an interactive remote shell.
- `Invoke-Command` for automation and running commands on one or many computers.
- `Test-WSMan` to verify the WinRM endpoint.

Windows Server 2012 and later normally have PowerShell Remoting enabled by default. If the configuration was changed, `Enable-PSRemoting -Force` can restore the standard setup.

## Scenario

An administrator wants to check the WinRM service on three servers without opening RDP sessions.

```powershell
Invoke-Command -ComputerName SERVER01,SERVER02,SERVER03 -ScriptBlock {
    Get-Service WinRM
}
```

The command executes on each target computer and returns the results to the management workstation.

## Diagnosis

If remoting fails, troubleshoot from the bottom up.

### 1. DNS

```powershell
Resolve-DnsName SERVER01
```

Prefer a hostname or FQDN in a domain environment because Kerberos normally depends on correct name resolution.

### 2. TCP connectivity

```powershell
Test-NetConnection SERVER01 -Port 5985
```

If `TcpTestSucceeded` is `False`, investigate routing, firewall, WinRM service state, or the listener.

### 3. WinRM endpoint

```powershell
Test-WSMan SERVER01
```

### 4. Target service

```powershell
Get-Service WinRM
```

### 5. Listener

```cmd
winrm enumerate winrm/config/listener
```

### 6. Firewall

```powershell
Get-NetFirewallRule |
    Where-Object DisplayName -Like "*Windows Remote Management*"
```

## Required permissions

The management computer does **not** have to be used by a local administrator merely to initiate a remote PowerShell connection.

What matters is authorization on the **target**.

A user can normally connect when allowed by the PowerShell session configuration and, in standard configurations, when the account is a member of:

- `Administrators`, or
- `Remote Management Users`

on the remote computer.

For delegated administration, prefer restricted endpoints such as **JEA** instead of giving broad local administrator rights.

Administrative elevation on the management workstation is still required when changing its local WSMan configuration, for example local `TrustedHosts` or WinRM settings.

## Kerberos vs TrustedHosts

In a normal Active Directory environment:

```powershell
Invoke-Command -ComputerName SERVER01 -ScriptBlock {
    hostname
}
```

should normally use domain authentication such as Kerberos.

Prefer:

```text
SERVER01
SERVER01.contoso.local
```

over a raw IP address.

Avoid the common workaround:

```powershell
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*"
```

unless there is a specific reason.

`TrustedHosts` is mainly for scenarios where normal server authentication through Kerberos cannot be used, such as some workgroup or IP-based connections. It should not be the default fix for a domain environment.

## Security note: HTTP 5985 is not automatically plaintext

A frequent misconception is:

```text
HTTP 5985 = unencrypted PowerShell traffic
```

That is incorrect.

With WinRM, message traffic is encrypted after authentication. In a normal domain scenario, **Kerberos + WinRM over HTTP/5985** is a standard secure configuration.

HTTPS/5986 can still be useful when TLS-based server authentication is needed, especially outside a normal Kerberos domain trust path.

## Double-hop problem

This is a classic AZ-802 scenario:

```text
ADMIN-PC
    |
    | first hop
    v
SERVER01
    |
    | second hop
    v
FS01
```

This may work:

```powershell
Invoke-Command SERVER01 {
    hostname
}
```

but this may fail:

```powershell
Invoke-Command SERVER01 {
    Get-ChildItem \\FS01\Data
}
```

even when the administrator normally has access to `\\FS01\Data`.

The reason is usually the **second-hop credential delegation problem**.

Do not automatically enable CredSSP. CredSSP can solve some double-hop scenarios, but it delegates reusable credentials to the remote computer and therefore increases risk if that computer is compromised.

Possible approaches include:

- Kerberos constrained delegation,
- resource-based constrained delegation,
- JEA / RunAs endpoints,
- carefully controlled explicit credentials,
- CredSSP only when justified.

## Practical repair sequence

Use this order:

```text
DNS
  ↓
routing / TCP 5985
  ↓
Test-WSMan
  ↓
WinRM service
  ↓
listener
  ↓
firewall
  ↓
authentication
  ↓
authorization / endpoint ACL
  ↓
double-hop, if the first connection already works
```

## Exam trap

A failed command such as:

```powershell
Invoke-Command SERVER01 {
    Get-ChildItem \\FS01\Data
}
```

does **not** necessarily mean WinRM is broken.

If the connection to `SERVER01` succeeds and only access from `SERVER01` to `FS01` fails, think:

> **second hop / credential delegation**

not:

> TCP 5985 firewall problem.

## Interview question

**Question:** How would you troubleshoot a failed `Invoke-Command` connection?

**Strong answer:**

> I would verify DNS resolution first, then test TCP connectivity to the WinRM port, normally 5985. Next I would use Test-WSMan, verify that the WinRM service and listener are working on the target, and confirm the firewall rules. If transport works, I would investigate authentication and authorization, including Kerberos and the PowerShell endpoint permissions. I would use TrustedHosts only when Kerberos cannot be used and would treat double-hop as a separate delegation problem.

## CAE / C1 phrase

**to narrow something down**

Meaning: to reduce the number of possible causes.

Example:

> Testing port 5985 and Test-WSMan first helps me narrow the problem down to transport, authentication, or authorization.

## Quick recall

```text
PowerShell Remoting on Windows → WinRM
HTTP                         → TCP 5985
HTTPS                        → TCP 5986
Interactive                  → Enter-PSSession
Automation                   → Invoke-Command
Check WinRM                   → Test-WSMan
Second remote resource fails → think double-hop
```

## References

- Microsoft Learn — about_Remote_Requirements  
  https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_remote_requirements
- Microsoft Learn — Security considerations for PowerShell Remoting using WinRM  
  https://learn.microsoft.com/en-us/powershell/scripting/security/remoting/winrm-security
- Microsoft Learn — Running Remote Commands  
  https://learn.microsoft.com/en-us/powershell/scripting/security/remoting/running-remote-commands
