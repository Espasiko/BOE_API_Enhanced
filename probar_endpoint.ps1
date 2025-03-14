# Script para probar el endpoint de búsqueda semántica directa
# Ejecutar con: .\probar_endpoint.ps1

$baseUrl = "http://127.0.0.1:8000"

Write-Host "Probando el endpoint de búsqueda semántica directa..." -ForegroundColor Cyan

# Datos para la búsqueda
$bodyJson = @{
    q = "protección de datos"
    limite = 10
    umbral = 0.3
} | ConvertTo-Json

# Mostrar la URL y los datos que se enviarán
Write-Host "URL: $baseUrl/api/semantica/directa/" -ForegroundColor Yellow
Write-Host "Datos: $bodyJson" -ForegroundColor Yellow

# Intentar la solicitud
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/semantica/directa/" -Method Post -Body $bodyJson -ContentType "application/json"
    
    # Mostrar resultados
    Write-Host "`n✅ Solicitud exitosa!" -ForegroundColor Green
    Write-Host "Total de resultados: $($response.total)" -ForegroundColor Green
    
    if ($response.resultados.Count -gt 0) {
        Write-Host "`nPrimeros resultados:" -ForegroundColor Green
        $response.resultados | Select-Object -First 3 | ForEach-Object {
            Write-Host "- $($_.titulo) (Score: $($_.score))" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "`n❌ Error al realizar la solicitud:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    # Intentar obtener más información sobre el error
    try {
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "Detalles del error: $($errorDetails | ConvertTo-Json)" -ForegroundColor Red
    } catch {
        Write-Host "No se pudieron obtener detalles adicionales del error" -ForegroundColor Red
    }
    
    # Verificar si es un error 404
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "`nEl error 404 indica que la ruta no existe. Posibles causas:" -ForegroundColor Yellow
        Write-Host "1. La URL está mal escrita" -ForegroundColor Yellow
        Write-Host "2. El endpoint no está registrado correctamente en urls.py" -ForegroundColor Yellow
        Write-Host "3. El servidor Django no ha cargado correctamente las URLs" -ForegroundColor Yellow
        
        # Sugerir soluciones
        Write-Host "`nSoluciones sugeridas:" -ForegroundColor Cyan
        Write-Host "1. Verificar que la función api_busqueda_semantica_directa existe en views_api.py" -ForegroundColor Cyan
        Write-Host "2. Verificar que la URL está correctamente registrada en urls.py" -ForegroundColor Cyan
        Write-Host "3. Reiniciar el servidor Django" -ForegroundColor Cyan
    }
}
