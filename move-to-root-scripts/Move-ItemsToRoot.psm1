Set-StrictMode -Version Latest

function Move-ItemsToRoot {
<#
.SYNOPSIS
Moves items from subdirectories into the root directory.

.DESCRIPTION
Enterprise-grade directory flattening tool with structured logging, filtering,
retry logic, and optional parallel execution.

.PARAMETER Path
Root directory.

.PARAMETER Include
Wildcard patterns to include (allowlist).

.PARAMETER Exclude
Wildcard patterns to exclude (denylist).

.PARAMETER MaxDepth
Maximum recursion depth.

.PARAMETER IncludeDirectories
Include directories in move.

.PARAMETER Overwrite
Overwrite existing files.

.PARAMETER LogPath
Path to JSON log file.

.PARAMETER Parallel
Enable parallel execution (PowerShell 7+).

.PARAMETER ThrottleLimit
Max parallel threads.

.PARAMETER RetryCount
Number of retries for locked files.

.PARAMETER RetryDelayMs
Delay between retries in milliseconds.

.PARAMETER PassThru
Return moved items.

.EXAMPLE
Move-ItemsToRoot -Path C:\Data -Include *.txt -Exclude *.log -WhatIf

.EXAMPLE
Move-ItemsToRoot -Path C:\Data -Parallel -ThrottleLimit 8 -RetryCount 5
#>

    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [Parameter(Position=0)]
        [ValidateNotNullOrEmpty()]
        [string]$Path = (Get-Location).Path,

        [string[]]$Include,
        [string[]]$Exclude,

        [ValidateRange(1,100)]
        [int]$MaxDepth = 100,

        [switch]$IncludeDirectories,
        [switch]$Overwrite,

        [string]$LogPath = (Join-Path $env:TEMP "Move-ItemsToRoot.json"),

        [switch]$Parallel,

        [ValidateRange(1,64)]
        [int]$ThrottleLimit = 4,

        [ValidateRange(0,10)]
        [int]$RetryCount = 3,

        [ValidateRange(100,10000)]
        [int]$RetryDelayMs = 500,

        [switch]$PassThru
    )

    begin {
        if ($Parallel -and $PSVersionTable.PSVersion.Major -lt 7) {
            throw "Parallel requires PowerShell 7+"
        }

        # Initialize log (NDJSON)
        New-Item -ItemType File -Path $LogPath -Force | Out-Null

        function Write-JsonLog {
            param(
                [string]$Level,
                [string]$Message,
                [string]$Source,
                [string]$Destination
            )

            $entry = [pscustomobject]@{
                timestamp   = (Get-Date).ToString("o")
                level       = $Level
                message     = $Message
                source      = $Source
                destination = $Destination
                host        = $env:COMPUTERNAME
                pid         = $PID
            }

            $entry | ConvertTo-Json -Compress | Add-Content -Path $LogPath
        }
    }

    process {
        if (-not (Test-Path -Path $Path -PathType Container)) {
            throw "Invalid directory: $Path"
        }

        $root = Get-Item $Path

        function Test-Filter {
            param($Item)

            if ($Include) {
                $match = $false
                foreach ($pattern in $Include) {
                    if ($Item.Name -like $pattern -or $Item.FullName -like $pattern) {
                        $match = $true
                        break
                    }
                }
                if (-not $match) { return $false }
            }

            if ($Exclude) {
                foreach ($pattern in $Exclude) {
                    if ($Item.Name -like $pattern -or $Item.FullName -like $pattern) {
                        return $false
                    }
                }
            }

            return $true
        }

        # Depth-aware enumeration
        $items = Get-ChildItem -Path $Path -Recurse -Force |
            Where-Object {
                $_.FullName -ne $root.FullName -and
                ($IncludeDirectories -or -not $_.PSIsContainer) -and
                ((($_.FullName -replace [regex]::Escape($root.FullName), '') -split '[\\/]').Count -le $MaxDepth)
            } |
            Where-Object { Test-Filter $_ }

        if (-not $items) { return }

        $moved     = [System.Collections.Concurrent.ConcurrentBag[object]]::new()
        $conflicts = [System.Collections.Concurrent.ConcurrentBag[object]]::new()

        $scriptBlock = {
            param($item, $rootPath, $Overwrite, $RetryCount, $RetryDelayMs, $LogPath)

            function Write-JsonLogLocal {
                param($Level, $Message, $Source, $Destination)

                $entry = @{
                    timestamp=(Get-Date).ToString("o")
                    level=$Level
                    message=$Message
                    source=$Source
                    destination=$Destination
                    pid=$PID
                } | ConvertTo-Json -Compress

                Add-Content -Path $LogPath -Value $entry
            }

            $destination = Join-Path $rootPath $item.Name

            if ((Test-Path -Path $destination) -and (-not $Overwrite)) {
                Write-JsonLogLocal "WARN" "Conflict" $item.FullName $destination
                return [pscustomobject]@{ Type="Conflict"; Item=$item }
            }

            $attempt = 0
            while ($attempt -le $RetryCount) {
                try {
                    Move-Item -Path $item.FullName -Destination $destination -Force:$Overwrite -ErrorAction Stop
                    Write-JsonLogLocal "INFO" "Moved" $item.FullName $destination
                    return [pscustomobject]@{ Type="Moved"; Item=$item }
                }
                catch {
                    if ($attempt -ge $RetryCount) {
                        Write-JsonLogLocal "ERROR" $_.Exception.Message $item.FullName $destination
                        return $null
                    }

                    Start-Sleep -Milliseconds $RetryDelayMs
                    $attempt++
                }
            }
        }

        if ($Parallel) {
            $results = $items | ForEach-Object -Parallel $scriptBlock `
                -ThrottleLimit $ThrottleLimit `
                -ArgumentList $root.FullName, $Overwrite, $RetryCount, $RetryDelayMs, $LogPath
        }
        else {
            $results = foreach ($item in $items) {
                if ($PSCmdlet.ShouldProcess($item.FullName, "Move to root")) {
                    & $scriptBlock $item $root.FullName $Overwrite $RetryCount $RetryDelayMs $LogPath
                }
            }
        }

        foreach ($r in $results) {
            if ($null -eq $r) { continue }

            if ($r.Type -eq "Moved") {
                $moved.Add($r.Item)
            }
            elseif ($r.Type -eq "Conflict") {
                $conflicts.Add($r.Item)
            }
        }

        Write-JsonLog "INFO" "Summary: moved=$($moved.Count) conflicts=$($conflicts.Count)" "" ""

        if ($PassThru) {
            return $moved
        }
    }
}

Export-ModuleMember -Function Move-ItemsToRoot