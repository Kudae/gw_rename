#!/bin/bash 

vi gw_rename.py

printf "Clear directories / files \n"
rm -v -R build dist gw_rename.spec __pycache__

printf "run pyinstaller for gw_rename.py\n"
/root/.pyenv/shims/python -m PyInstaller gw_rename.py --onefile

printf "copy file over to remote server\n"
sshpass -p 'vpn123' scp dist/gw_rename admin@172.25.84.166:/home/admin
