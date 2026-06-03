try {
    $VaultExe = "C:\vault\vault.exe"

    Get-Process vault -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force
        Write-Host "Killed Vault process $($_.Id)"
    }

    Start-Sleep -Seconds 1

    $env:VAULT_DEV_ROOT_TOKEN_ID = "MTR"
    $env:VAULT_ADDR = "http://127.0.0.1:8200"
    $env:VAULT_TOKEN = "MTR"

    Start-Process -FilePath $VaultExe `
        -ArgumentList "server -dev -dev-root-token-id=MTR -dev-listen-address=127.0.0.1:8200" `
        -WindowStyle Hidden

    Write-Host "Vault process started"

    $deadline = (Get-Date).AddSeconds(30)

    do {
        Start-Sleep -Milliseconds 500

        & $VaultExe status *> $null
        $statusCode = $LASTEXITCODE

        if ($statusCode -eq 0 -or $statusCode -eq 2) {
            Write-Host "Vault is ready"
            exit 0
        }

    } while ((Get-Date) -lt $deadline)

    Write-Host "Vault did not become ready"
    Get-Process vault -ErrorAction SilentlyContinue
    exit 1
}
catch {
    Write-Host "Failed to start Vault: $_"
    exit 1
}