@echo off
FOR /F "tokens=2,3" %%A IN ('ping %computername% -n 1 -4') DO IF "from"== "%%A" set "IP=%%~B"
echo %IP:~0,-1% >> C:/tmp/hosts
