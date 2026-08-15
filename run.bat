@echo off
setlocal
cd /d "%~dp0"

echo === Analizator Gieldowy + TIMDR ===
echo Instaluje zaleznosci (Flask, pandas, numpy, yfinance, termcolor)...
python -m pip install --quiet flask pandas numpy termcolor
if errorlevel 1 (
    echo BLAD: nie udalo sie zainstalowac zaleznosci. Sprawdz czy Python i pip sa zainstalowane.
    pause
    exit /b 1
)

REM WAZNE: yfinance jest zawsze dociagany do NAJNOWSZEJ wersji (--upgrade),
REM nie tylko instalowany "jesli brakuje". Yahoo Finance w 2025/2026
REM wprowadzil ochrone antybotowa (Cloudflare) - stare wersje yfinance
REM (bez biblioteki curl_cffi) dostaja w odpowiedzi puste dane / błąd
REM JSONDecodeError zamiast prawdziwych danych. Jesli masz juz starsza
REM wersje yfinance zainstalowana z wczesniej, samo "pip install yfinance"
REM (bez --upgrade) NIC by nie zmienilo, bo pip uznaje wymaganie za juz
REM spelnione.
echo Aktualizuje yfinance do najnowszej wersji (wymagane dla obejscia ochrony Yahoo)...
python -m pip install --quiet --upgrade yfinance
if errorlevel 1 (
    echo BLAD: nie udalo sie zainstalowac/zaktualizowac yfinance.
    pause
    exit /b 1
)

echo.
echo Uruchamiam serwer API pod http://127.0.0.1:5000 ...
echo   - Dashboard/przycisk "Dane demo" dziala zawsze (dane syntetyczne).
echo   - Przycisk "Analizuj (zywe dane)" pobierze prawdziwe dane z Yahoo
echo     Finance, o ile ten komputer ma dostep do internetu.
echo.

start "" http://127.0.0.1:5000
python api.py

pause
