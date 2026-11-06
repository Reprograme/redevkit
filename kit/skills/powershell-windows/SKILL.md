---
name: powershell-windows
description: PowerShell pitfalls on Windows - operators, quoting, encoding, paths, errors; use when writing or running PowerShell.
---

# PowerShell Windows Patterns

> Critical patterns and pitfalls for Windows PowerShell 5.1 and PowerShell 7+ (`pwsh`).
> Check the version first: `$PSVersionTable.PSVersion`.

---

## 1. Operator Syntax Rules

### CRITICAL: Parentheses Required

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| `if (Test-Path "a" -or Test-Path "b")` | `if ((Test-Path "a") -or (Test-Path "b"))` |
| `if (Get-Item $x -and $y -eq 5)` | `if ((Get-Item $x) -and ($y -eq 5))` |

**Rule:** Each cmdlet call MUST be in parentheses when using logical operators.

---

## 2. Unicode/Emoji Restriction

### CRITICAL: Prefer ASCII in Scripts

Windows PowerShell 5.1 reads a UTF-8 script **without BOM** as the ANSI code page, so emoji
and accented characters break parsing or output. PowerShell 7 reads UTF-8 correctly. Keep
scripts ASCII, or save them as UTF-8 with BOM when 5.1 must run them.

| Purpose | ❌ Don't Use | ✅ Use |
|---------|-------------|--------|
| Success | ✅ ✓ | [OK] [+] |
| Error | ❌ ✗ 🔴 | [!] [X] |
| Warning | ⚠️ 🟡 | [*] [WARN] |
| Info | ℹ️ 🔵 | [i] [INFO] |
| Progress | ⏳ | [...] |

**Rule:** Use ASCII status markers in scripts that may run on Windows PowerShell 5.1.

---

## 3. Null Check Patterns

### Always Check Before Access

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| `$array.Count -gt 0` | `$array -and $array.Count -gt 0` |
| `$text.Length` | `if ($text) { $text.Length }` |

---

## 4. String Interpolation

### Property Access Needs a Subexpression

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| `"Value: $obj.prop"` (expands only `$obj`) | `"Value: $($obj.prop)"` |

For long expressions, store the value in a variable first:

```powershell
$value = $obj.prop.sub
Write-Output "Value: $value"
```

Single quotes never expand: `'Cost: $5'` stays literal.

---

## 5. Error Handling

### ErrorActionPreference

| Value | Use |
|-------|-----|
| Stop | Development and scripts that must fail fast |
| Continue | Scripts that log and keep going |
| SilentlyContinue | When errors are expected and handled |

### Try/Catch Pattern

- `try/catch` only catches terminating errors; add `-ErrorAction Stop` to the cmdlet
- Use `finally` for cleanup
- Prefer returning after the `try/catch` block
- A failing native command (`git`, `npm`) does not throw; check `$LASTEXITCODE`

---

## 6. File Paths

### Windows Path Rules

| Pattern | Use |
|---------|-----|
| Literal path | `C:\Users\User\file.txt` |
| Variable path | `Join-Path $env:USERPROFILE "file.txt"` |
| Relative to script | `Join-Path $PSScriptRoot "data"` |
| Path with spaces | Always quote: `"C:\Program Files\App"` |

**Rule:** Use `Join-Path` instead of string concatenation.

---

## 7. Array Operations

### Correct Patterns

| Operation | Syntax |
|-----------|--------|
| Empty array | `$array = @()` |
| Add item (small arrays) | `$array += $item` |
| Many items | `$list = [System.Collections.Generic.List[object]]::new(); $list.Add($item)` |
| Force array result | `@(Get-ChildItem *.log)` |

---

## 8. JSON Operations

### CRITICAL: Depth Parameter

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| `ConvertTo-Json` | `ConvertTo-Json -Depth 10` |

**Rule:** Always specify `-Depth` for nested objects (the default is 2 and silently truncates).

### File Operations

| Operation | Pattern |
|-----------|---------|
| Read | `Get-Content "file.json" -Raw \| ConvertFrom-Json` |
| Write | `$data \| ConvertTo-Json -Depth 10 \| Set-Content "file.json" -Encoding UTF8` |

---

## 9. Chaining and Redirection

| Need | Windows PowerShell 5.1 | PowerShell 7+ |
|------|------------------------|---------------|
| Run B only if A succeeds | `A; if ($?) { B }` | `A && B` |
| Discard errors | `2>$null` | `2>$null` |
| Set an environment variable | `$env:NAME = "x"` | same |
| Run an exe whose path has spaces | `& "C:\Program Files\App\app.exe" arg` | same |

Bash syntax (`export`, `VAR=x cmd`, `[ -f x ]`, backticks for substitution) does not work.

---

## 10. Common Errors

| Error Message | Cause | Fix |
|---------------|-------|-----|
| "parameter 'or'" | Missing parentheses | Wrap cmdlets in () |
| "Unexpected token" | Non-ASCII character in a 5.1 script | Use ASCII or UTF-8 with BOM |
| "Cannot find property" | Null object | Check null first |
| "Cannot convert" | Type mismatch | Use .ToString() or a cast |
| "is not recognized as the name of a cmdlet" | Bash command or missing exe | Use the PowerShell equivalent |

---

## 11. Script Template

```powershell
# Strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Paths
$ScriptDir = $PSScriptRoot

# Main
try {
    # Logic here
    Write-Output "[OK] Done"
    exit 0
}
catch {
    Write-Warning "Error: $_"
    exit 1
}
```

---

> **Remember:** PowerShell has unique syntax rules. Parentheses, encoding and null checks are
> non-negotiable.
