@echo off
echo Starting ZetsuServ Application...
echo.

REM Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

REM Initialize database if needed
echo Initializing database...
python -m flask init-db 2>nul

REM Create default admin (optional - will prompt for password)
REM python -m flask create-admin

echo.
echo Starting Flask server...
echo Application will be available at http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

REM Run the application
python app.py