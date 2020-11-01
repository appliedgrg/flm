@echo off
set scriptName=ForestLineMapper.py
set pro=%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\propy
set desktop=c:\python27\python.exe
set default27=c:\python27\

if exist "%pro%.bat" ( 
	call "%pro%" %scriptName%
	goto :break
)

if exist %default27% (
	for /d %%i in (%default27%*) do (
		if exist %%i\python.exe (
			%%i\python.exe %scriptName% %*
			goto :break
		)
	)
)

if exist %desktop% (
	%desktop% %scriptName% %* 
	goto :break
) else (
	python %scriptName% %* 
)

if errorlevel 1 (
		echo Python was not found.
		pause
)

:break