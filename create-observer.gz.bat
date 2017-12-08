C:\"Program Files"\7-Zip\7z.exe a -ttar mqtt-observer-%date:~6,4%%date:~3,2%%date:~0,2%.tar -xr!_SYNCAPP -xr!*.tgz -xr!*.vs -xr!*.pyc -xr!*.log.* ./dist ./src build.bat README.md "MQTT Observer.pyproj" create-observer.gz.bat logging.ini
;C:\"Program Files"\7-Zip\7z.exe a -tgzip mqtt-observer-1.0-%date:~6,4%%date:~3,2%%date:~0,2%.tgz mqtt-observer-%date:~6,4%%date:~3,2%%date:~0,2%.tar 
;del mqtt-observer-%date:~6,4%%date:~3,2%%date:~0,2%.tar
