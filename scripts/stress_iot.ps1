param (
    [string]$ApiUrl = "http://localhost:8081",
    [int]$Concurrency = 30,
    [int]$DurationSeconds = 300
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🚀 DISPARANDO CARGA SIMULADA DE SENSORES IOT (POWERSHELL)" -ForegroundColor Yellow
Write-Host "Endpoint: $ApiUrl/api/sensores/telemetria" -ForegroundColor White
Write-Host "Concorrência: $Concurrency threads | Duração: $DurationSeconds s" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

$endpoint = "$ApiUrl/api/sensores/telemetria?stress_cpu=true"
$body = '{"sensorId":"SENSOR-PWSH","temperatura":80.0,"pressao":2.0}'

$scriptBlock = {
    param($url, $payload, $endTime)
    while ((Get-Date) -lt $endTime) {
        try {
            Invoke-RestMethod -Uri $url -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 3 | Out-Null
        } catch {}
        Start-Sleep -Milliseconds 50
    }
}

$endTime = (Get-Date).AddSeconds($DurationSeconds)
$jobs = @()

for ($i = 0; $i -lt $Concurrency; $i++) {
    $jobs += Start-Job -ScriptBlock $scriptBlock -ArgumentList $endpoint, $body, $endTime
}

Write-Host "Injeção iniciada com $($jobs.Count) jobs em background." -ForegroundColor Green
Write-Host "Acompanhe o HPA no terminal: kubectl get hpa -n mecaniqa -w" -ForegroundColor Magenta

while ((Get-Date) -lt $endTime) {
    $remaining = [int]($endTime - (Get-Date)).TotalSeconds
    Write-Host "Tempo restante: $remaining s..."
    Start-Sleep -Seconds 10
}

$jobs | Stop-Job | Remove-Job
Write-Host "✅ Teste de carga finalizado com sucesso." -ForegroundColor Green

