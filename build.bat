pyrcc5 src/observer.qrc -o src/observer_rc.py
;pyinstaller -F -n mqtt-observer -i src/observer.ico -w src/main.py