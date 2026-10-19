@echo off
call "%USERPROFILE%\anaconda3\Scripts\activate.bat" bimbem
set PATH=C:\openstudio-3.9.0\bin;%PATH%
cd /d "%~dp0"
python -m streamlit run app_inic.py
pause
