import os
from os import path
from signal import pause
import sys
import requests
from requests import api 
import urllib3
import json
import time
import subprocess
import traceback
import logging

#remove insecure https warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#Global Variables
global gwpath
gwpath = '/tmp/gw_rename_project'
global log
log = f'{gwpath}/gw_rename_api.log'
global cmasid
cmasid = f'{gwpath}/gw_rename_sid.txt'
global shell
shell = '#!/bin/bash'
global cpprofile
cpprofile = 'source /etc/profile.d/CP.sh'

#help menu
def helpmenu():

    global debug
    if len(sys.argv) > 1 and sys.argv[1] == "-h": 
        print(
            '''
            [ Help Menu ]

            Usage: 
            ./gw_rename OPTIONS

            Options:
            -d = Debugging
            -h = Usage 

            Notes: 
            Built for x86_64 linux systems. 

            This is a pyinstaller onefile binary
            that includes all required modules. 
            '''
        )
        quit() 
    elif len(sys.argv) > 1 and sys.argv[1] == "-d":
        print('\n[ Debug Mode Enabled ]\n') 
        debug = 1
    else: 
        print('\n[ Debug Mode Disabled ]\n')
        debug = 0
    
    return debug
    

def askConfig():

    print("\n[ Provide Configuration ]\n")

    global username, password, domain_name, cma_ip, api_ip, api_port

    username = input("Username: ")
    password = input("Password: ")
    domain_name = input("Domain Name (in SmartConsole): ")
    cma_ip = input("Primary CMA IP: ")
    api_ip = input("API (MDM) IP Address: ")
    api_port = input("API Port: ")

    formatanswer = f"""
                        username = {username}
                        password = {password}
                        Domain Name = {domain_name}
                        CMA IP = {cma_ip}
                        API IP = {api_ip}
                        API Port = {api_port}
                        """  

    question = input(f"\n{formatanswer}\nIs this information correct? (y/n) ")   
    if question == "n":
        askConfig()
    elif question == "y": 
        print("\nContinuing... \n")


# make code directory / clear log files 
def gw_mkdir():

    print(f'[ Dir: {gwpath} ]\n')

    if os.path.isdir(gwpath):
        print('... Exists!\n')
        print('\n[ Clearing old logs ]\n')
        os.system(f'rm -v {gwpath}/gw_rename_*')
    else:
        print(f'... Created!\n')
        os.mkdir(gwpath)

    
# sleep function
def sleeptime(timeval): 
    time.sleep(timeval)

# take any input to pause debug 
def pause_debug():
    input("[ DEBUG ] Press any key to continue...\n\n")    


# capture api responses/information
def api_debug(defname, url, headers, body, result, api_post): 

    if len(sys.argv) > 1 and sys.argv[1] == "-d":
        apiBugs = [
        f"\n\n[ {defname} ]\n",
        f"{defname} : URL : {url} \n",
        f"{defname} : Headers : {headers} \n",
        f"{defname} : Body : {body} \n",
        f"{defname} : JSON RESPONSE : \n{result}\n",
        f"{defname} : Status Code: {api_post.status_code}\n",
        ]
        f = open(log, "a")
        f.writelines(apiBugs)
        f.close()


# API Login
def login(domain): 

    print("\n[ Login to API ]\n")

    defname = f"API : Login : {domain}"
    
    api_url = f'{url}/login'
    headers = {'Content-Type' : 'application/json'}
    body = {'user' : f'{username}', 
            'password' : f'{password}',
            'domain' : f'{domain}'}

    api_post = requests.post(api_url, data = json.dumps(body), headers=headers, verify=False)
    result = json.loads(api_post.text)

    response = api_post.status_code
    if response == 200: 
        print(f'{response}... Log in Successful.\n')
    else: 
        print(f'{response}... Login Failed.\n')


    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    #write session id to OS for later use
    cmatmp = f'{gwpath}/gw_rename_cmatmp.sh'
    cmacmd = f'mgmt_cli login -r true -d {domain} > {cmasid}'
    bash_script(cmacmd, cmatmp)

    return result


# API Publish
def publish(domain, sid): 

    print("\n[ Publish Changes ]\n")

    defname = f"API : Publish : {domain}"

    api_url = f'{url}/publish'
    x = sid["sid"]
    headers = {'Content-Type' : 'application/json',
                'X-chkp-sid' : f'{x}'} 
    body = {}

    api_post = requests.post(api_url, data=json.dumps(body), headers=headers, verify=False)
    result = api_post.json() 

    response = api_post.status_code
    if response == 200: 
        print(f'{response}... Publish Successful.\n')
    else: 
        print(f'{response}... Publish Failed.\n')

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    if len(sys.argv) > 1 and sys.argv[1] == "-d":
        with open (f'{domain}_publish.json', 'a') as f:
         f.write(json.dumps(result))


# API Logout
def logout(sid): 

    print("\n[ Log out of session ]\n")

    defname = f"API : Logout : {sid['sid']}"

    api_url = f'{url}/logout'
    x = sid["sid"]
    headers = {'Content-Type' : 'application/json',
                'X-chkp-sid' : f'{x}'} 
    body = {}
    api_post = requests.post(api_url, data=json.dumps(body), headers=headers, verify=False)
    result = api_post.json()

    response = api_post.status_code
    if response == 200: 
        print(f'{response}... Logged out\n')
    else: 
        print(f'{response}... Login failed\n')


    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

# create scripts to run on mds
def bash_script(cmd, script):

    mdsbash=f"""{shell} 
{cpprofile}

{mdsenv}
{cmd} 
"""
    newscript = f'{script}'

    if debug ==1:
        print(f'[ contents ]\n{mdsbash}\n')
        print(f'[ script]\n{newscript}\n')
        print('[[ Does everything look right? ]]\n')
        pause_debug()

    with open(script, 'w') as f: 
        f.write(mdsbash)

    os.system(f"chmod +x {newscript}")
    runcmd = f"{newscript}"
    
    vallist = subprocess.check_output(runcmd, shell=True, text=True)

    print(f"[ RESULT ]\n{newscript}: {vallist}\n\n")

    return vallist


def gw_info(): 

    print("\n[ List GW and SIC Names / Convert Lists ]\n")

     # (oldmemlist) cluster member names list on CMA
    global oldmemlist
    memcmd = """cpmiquerybin attr "" network_objects "(class='cluster_member')" -a __name__"""
    memscript = f'{gwpath}/gw_rename_oldmemlist.sh'
    oldmemlist = bash_script(memcmd, memscript).split()
    
    # (cmiplist) cluster member IP addresses list on CMA
    global cmiplist
    cmiplist = []
    for cmname in oldmemlist:
        cmcmd = f"""cpmiquerybin attr "" network_objects "(name='{cmname}')" -a ipaddr | tr -d '[:space:]'"""
        cmscript = f'{gwpath}/gw_rename_cmiplist.sh'
        cmiplistnew = bash_script(cmcmd, cmscript)
        cmiplist.append(cmiplistnew)

    # get SIC name of each cluster member
    global oldsiclist
    oldsiclist = []
    for sic in oldmemlist: 
        siccmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
        sicscript = f'{gwpath}/gw_rename_oldsiclist.sh'
        oldsiclistnew = bash_script(siccmd, sicscript)
        oldsiclist.append(oldsiclistnew)

    # debug 
    if debug == 1: 
        print(f"Old Cluster Members List\n{oldmemlist}\n")
        print(f"Cluster Member IP List: {cmiplist}\n")
        print(f"Old SIC List\n{oldsiclist}\n")
        pause_debug()


def dbeditcreate():

    # (newmemlist) Ask user for new name of each cluster member 
    global newmemlist
    newmemlist = []
    for mem in oldmemlist:
        newmem = input(f"Type new name for {mem}: ")
        newmemlist.append(newmem)

    global newsiclist
    newsiclist = []
    for x,y in zip(oldsiclist, oldmemlist):
        for z in newmemlist:
            if y in x and not any(z in s for s in newsiclist):
                newsiclist.append(x.replace(y, z))

    # debug
    if debug == 1: 
        print(f"New Cluster Member List\n{newmemlist}\n")
        print(f"New SIC List\n{newsiclist}\n")
        pause_debug()


    #Open .dbedit file and write changes. 
    # Make sic changes to old newtork objects
    with open(dbeditfile, 'a') as f:
        for x,y in zip(oldmemlist,newsiclist): 
            output = f"""modify network_objects {x} sic_name "{y}"\n"""
            f.write(output)

    # Update old network object name with new name 
    with open(dbeditfile, 'a') as f:
        for x,y in zip(oldmemlist,newmemlist): 
            output = f"""rename network_objects {x} {y}\n"""
            f.write(output)

    with open(dbeditfile, 'a') as f: 
        output = "quit -update_all"
        f.write(output)

    # debug 
    if debug == 1: 
        print("\n[Compiled dbedit file]\n")
        os.system(f"cat {dbeditfile}")
        pause_debug()


def gw_sic_reset():

    print("\n[ Reset SIC on Gateway Side ]\n")

    for member,newmem in zip(oldmemlist,newmemlist): 
        sicreset = f'{gwpath}/gw_rename_{member}_sic_reset.sh'
        with open(sicreset, 'w') as f: 
                bashfile = f"""#!/bin/bash
. /etc/profile.d/CP.sh

clish -sc "set hostname {newmem}"
cp_conf sic init vpn123 norestart
cpwd_admin stop -name CPD -path "$CPDIR/bin/cpd_admin" -command "cpd_admin stop" >/home/admin/cpdstop
cpwd_admin start -name CPD -path "$CPDIR/bin/cpd" -command "cpd" > /home/admin/cpdstart

FAIL="$(cat /home/admin/cpdstart | grep "CPD is alive")"
SUCCESS="$(cat /home/admin/cpdstart | grep "Process CPD started successfully")"
if [ -n "$SUCCESS" ]
then
    echo "SUCCESS"
else
    if [ -n "$FAIL" ]
    then
        echo "FAILURE"
    fi
fi"""
                f.write(bashfile)           

    
    # send bash file to gateway and execute sic reset
    

    for member,ip in zip(oldmemlist,cmiplist):
        sendsic = f'{gwpath}/gw_rename_{member}_send_sic.sh'
        commands = f"""cprid_util -debug -server {ip} -verbose putfile -local_file "{gwpath}/gw_rename_{member}_sic_reset.sh" -remote_file "/home/admin/{member}_sic_reset.sh" -perms 700
cprid_util -debug -server {ip} -verbose rexec -rcmd /home/admin/{member}_sic_reset.sh
"""
        bash_script(commands, sendsic)

        if debug == 1:
            print(commands)


def dbedit_apply(): 

    print("\n[ Apply dbedit configuration to CMA ]\n")

    commands= f"""dbedit -local -f {dbeditfile}"""

    if debug == 1:
        with open(dbeditfile, 'r') as f:
            f.read()
        pause_debug()

    bash_script(commands, dbeditapply)

    if debug == 1: 
        print("[ New Configuration Hostname / SIC ]")

        new_memcmd = """cpmiquerybin attr "" network_objects "(class='cluster_member')" -a __name__"""
        new_memscript = f'{gwpath}/gw_rename_newmemlist_2.txt'
        new_oldmemlist = bash_script(new_memcmd, new_memscript).split()

        new_oldsiclist = []
        for sic in new_oldmemlist: 
            new_siccmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
            new_sicscript = f'{gwpath}/gw_rename_newsiclist_2.txt'
            new_oldsiclistnew = bash_script(new_siccmd, new_sicscript)
            new_oldsiclist.append(new_oldsiclistnew)

        print(f"NEW Cluster Members List\n{new_oldmemlist}\n")
        print(f"NEW SIC List\n{new_oldsiclist}\n")
        pause_debug()


def api_sic(): 

    print("\n[ Establish SIC on API and update member names ]\n")

    clulist = f'{gwpath}/gw_rename_clulist.txt'

    commands = """cpmiquerybin attr "" network_objects "(class='gateway_cluster')" -a __name__"""
    clulistnew = bash_script(commands, clulist).split()

    if debug == 1: 
        print(f'[ clulist ]\n{clulistnew}')
        pause_debug()

    newclulist = input("\nPlease enter new name for Cluster Object: ")

    esic = f'{gwpath}/gw_rename_establishsic.sh'

    
    
    for i,item in enumerate(newmemlist):
        command = f"""mgmt_cli -s {cmasid} \ 
set simple-cluster name "{clulistnew[0]}" ignore-warnings "true" \ \n"""
        command1 = f"""
members.update.{i}.name "{item}" \ 
members.update.{i}.one-time-password "vpn123" \ 
"""
        command = command + command1 + '\n'
 
        # if debug == 1:
        print(f'api_sic command:\n{command}')
        pause_debug()

    bash_script(command, clulist)

    publish(domain_name, sid)

    #Update cluster member name...
    

def main(): 

    helpmenu()

    askConfig()

    #global url variable, import local config file
    global url
    url = f'https://{api_ip}:{api_port}/web_api'
    print(f"\n[ Global URL Variable]\n{url}\n")
    global dbeditfile
    dbeditfile = f'{gwpath}/gw_rename_{domain_name}.dbedit'
    global dbeditapply
    dbeditapply = f'{gwpath}/gw_rename_{domain_name}_dbedit_apply.sh'
    global mdsenv
    mdsenv = f'mdsenv {cma_ip}'
    
    # create new log directory, delete old log files
    gw_mkdir()

    #login to domain 
    global sid
    sid = login(domain_name)

    # get list of CMA's and CMA IP's from system 
    gw_info()

    # create dbedit file
    dbeditcreate()
    
    # create bash file and send to gateways to reset sic 
    gw_sic_reset()

    # apply dbedit change 
    dbedit_apply()

    # apply api changes to establish sic
    api_sic()


if __name__=="__main__":
    try:
        main()
    except Exception as e:
        logging.error(traceback.format_exec())
        print("[Logging user out]\n")
        logout(sid)
        sys.exit(0)
        os._exit(0)
    finally:
        print("[Logging user out]\n")
        logout(sid)
        sys.exit(0)
        os._exit(0)
