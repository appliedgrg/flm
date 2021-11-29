@echo off
set scriptName=ForestLineMapper.py
set pro=%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\propy

if exist "%pro%.bat" (
	call "%pro%" %scriptName%
	goto :break
)

python %scriptName% %*

if errorlevel 1 (
		echo Python was not found.
		pause
)

:break