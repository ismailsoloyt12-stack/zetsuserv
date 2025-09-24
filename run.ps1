# ZetsuServ Application Startup Script

Write-Host "Starting ZetsuServ Application..." -ForegroundColor Green
Write-Host ""

# Set Flask environment variables
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"

# Initialize database if needed
Write-Host "Initializing database..." -ForegroundColor Yellow
python -m flask init-db 2>$null

Write-Host ""
Write-Host "Starting Flask server..." -ForegroundColor Green
Write-Host "Application will be available at http://localhost:5000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Run the application
python app.py