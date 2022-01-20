import os
from os import path
from socket import timeout
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
global shell
shell = '#!/bin/bash'
global cpprofile
cpprofile = 'source /etc/profile.d/CP.sh'

global gwpath
gwpath = '/tmp/gw_rename_project'

global log
log = f'{gwpath}/gw_rename_api.log'
global cmasid
cmasid = f'{gwpath}/gw_rename_sid.txt'
global cmatmp
cmatmp = f'{gwpath}/gw_rename_tmprun.sh'
global clulist
clulist = f'{gwpath}/gw_rename_clulist.txt'
global clurename
clurename = f'{gwpath}/gw_rename_clurename.sh'
global esic
esic = f'{gwpath}/gw_rename_establishsic.sh'


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


def question(stuff):
    while True:
        answer = input(f"\n{stuff}: ")
        if len(answer) is not 0:
            False
            return answer 


def askConfig():

    print("\n[ Provide API/CMA/Domain Configuration ]\n")

    global username, password, domain_name, cma_ip, api_ip, api_port

    username = question('Username')
    password = question("Password")
    api_ip = question("API (MDM) IP Address")
    api_port = question("API Port")
    domain_name = question("Domain Name (in SmartConsole)")
    cma_ip = question("Primary CMA IP")

    formatanswer = f"""username = {username}
password = {password}
API IP = {api_ip}
API Port = {api_port}
Domain Name = {domain_name}
CMA IP = {cma_ip}
"""  

    result = question(f"\n{formatanswer}\nIs this information correct? (y/n)")   
    if result == "n":
        askConfig()
    elif result == "y": 
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


def pause_script():
    input("\n\n--- Check and Verify. Press any key to continue ---") 


# capture api responses/information
def api_debug(defname, apiurl, headers, body, result, api_post): 

    apiBugs = [
    f"\n\n[ {defname} ]\n",
    f"{defname} : URL : {apiurl} \n",
    f"{defname} : Headers : {headers} \n",
    f"{defname} : Body : {body} \n",
    f"{defname} : JSON RESPONSE : \n{result}\n",
    f"{defname} : Status Code: {api_post.status_code}\n"
    ]

    with open(log, 'a') as f:
        f.writelines(apiBugs)


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

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    response = api_post.status_code
    if response == 200: 
        print(f'{response}... Log in Successful.\n')
    else: 
        print(f'{response}... Login Failed.\n')

    #write session id to OS for later use
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

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    response = api_post.status_code
    if response == 200: 
        print(f'{response}... Publish Successful.\n')
    else: 
        print(f'{response}... Publish Failed.\n')


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

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    response = api_post.status_code
    if response == 200: 
        print(f'{response}... Logged out\n')
    else: 
        print(f'{response}... Logout failed\n')


# create scripts to run on mds
def bash_script(cmd, script):

    mdsbash=f"""{shell} 
{cpprofile}

{mdsenv}
{cmd} 
"""
    newscript = f'{script}'

    if debug == 1:
        print(f'[ contents ]\n{mdsbash}\n')
        print(f'[ script]\n{newscript}\n')
        print('[[ Does everything look right? ]]\n')
        pause_debug()

    with open(script, 'w') as f: 
        f.write(mdsbash)

    os.system(f"chmod +x {newscript}")
    runcmd = f"{newscript}"
    
    vallist = subprocess.check_output(runcmd, shell=True, text=True)

    if debug == 1:
        print(f"[ RESULT ]\n{newscript}: {vallist}\n\n")

    return vallist


def gw_info(): 

    print("\n[ List GW and SIC Names / Convert Lists ]\n")

    global oldclulist, oldmemlist, oldsiclist, cmiplist, oldgwlist, oldgwsiclist, gwiplist

    ### GATEWAY LISTS ###

    # gateway name list 
    cmd = f"""cpmiquerybin attr "" network_objects "(class='gateway_ckp')" -a __name__"""
    script = f'{gwpath}/gw_rename_oldgwlist.sh'
    oldgwlist = bash_script(cmd, script).split()

    # gateway IP address list 
    gwiplist = []
    for gw in oldgwlist:
        cmd = f"""cpmiquerybin attr "" network_objects "(name='{gw}')" -a ipaddr | tr -d '[:space:]'"""
        script = f'{gwpath}/gw_rename_gwiplist.sh'
        gwiplistnew = bash_script(cmd, script)
        gwiplist.append(gwiplistnew)

    # gateway sic list 
    oldgwsiclist = []
    for sic in oldgwlist:
        cmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
        script = f'{gwpath}/gw_rename_oldgwsiclist.sh'
        oldgwsiclistnew = bash_script(cmd, script)
        oldgwsiclist.append(oldgwsiclistnew)

    print(f"OLD GW  List\n{oldgwlist}\n")
    print(f"OLD SIC List\n{oldgwsiclist}\n")
    print(f"Cluster Member IP List\n{gwiplist}\n")
    pause_script()

    
    ### CLUSTER MEMBER LISTS ###

     # cluster member name list
    cmd = """cpmiquerybin attr "" network_objects "(class='cluster_member')" -a __name__"""
    script = f'{gwpath}/gw_rename_oldmemlist.sh'
    oldmemlist = bash_script(cmd, script).split()
    
    # cluster member IP address list
    cmiplist = []
    for cm in oldmemlist:
        cmd = f"""cpmiquerybin attr "" network_objects "(name='{cm}')" -a ipaddr | tr -d '[:space:]'"""
        script = f'{gwpath}/gw_rename_cmiplist.sh'
        cmiplistnew = bash_script(cmd, script)
        cmiplist.append(cmiplistnew)

    # SIC name of each cluster member
    oldsiclist = []
    for sic in oldmemlist: 
        cmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
        script = f'{gwpath}/gw_rename_oldsiclist.sh'
        oldsiclistnew = bash_script(cmd, script)
        oldsiclist.append(oldsiclistnew)

    # old cluster list
    commands = """cpmiquerybin attr "" network_objects "(class='gateway_cluster')" -a __name__"""
    oldclulist = bash_script(commands, clulist).split()

    # verify with user 
    print(f"OLD Cluster Members List\n{oldmemlist}\n")
    print(f"OLD SIC List\n{oldsiclist}\n")
    print(f'OLD CLU List\n{oldclulist}\n')
    print(f"Cluster Member IP List\n{cmiplist}\n")
    pause_script()


def dbeditcreate():

    print('\n[ Dbedit File Create ]\n')

    global newmemlist, newsiclist, newgwlist, newgwsiclist, newclulist

    # Ask user for new name of each gateway 
    # def entry_list(x,y,z): 
    #     for i in x:
    #         a = question(y)
    #         z.append(a)

    # newgwlist = []
    # q = f"Enter new name for gateway {i}"
    # entry_list(oldgwlist, newgwlist, q)

    newgwlist = [] 
    for gw in oldgwlist:
        newgw = question(f"Enter new name for gateway {gw}")
        newgwlist.append(newgw)

    # Make new sic entries 
    newgwsiclist = [] 
    for x,y in zip(oldgwsiclist, oldgwlist):
        for z in newgwlist:
            if y in x and not any(z in s for s in newgwsiclist):
                newgwsiclist.append(x.replace(y, z))

    print(f"NEW -- Gateway List\n{newgwlist}\n")
    print(f"NEW -- Gateway SIC List\n{newgwsiclist}\n")
    pause_script()


    newclulist = []
    for x in oldclulist:
        result = question(f"Enter new cluster object name {x}")
        newclulist.append(result)

    # Ask user for new name of each cluster member 
    newmemlist = []
    for mem in oldmemlist:
        newmem = question(f"Enter new name for cluster member {mem}")
        newmemlist.append(newmem)

    # Make new sic entries 
    newsiclist = []
    for x,y in zip(oldsiclist, oldmemlist):
        for z in newmemlist:
            if y in x and not any(z in s for s in newsiclist):
                newsiclist.append(x.replace(y, z))

    print(f"NEW -- Cluster Member List\n{newmemlist}\n")
    print(f"NEW -- SIC List\n{newsiclist}\n")
    pause_script()


    ### Make dbedit file ###

    # Modify SIC entries 
    def mod_sic(a, b):
        with open(dbeditfile, 'a') as f:
            for x,y in zip(a, b):
                output = f"""modify network_objects {x} sic_name "{y}"\n"""
                f.write(output)

    
    mod_sic(oldgwlist, newgwsiclist)
    mod_sic(oldmemlist, newsiclist)

    # Modify network object names
    def mod_net(a, b):
        with open(dbeditfile, 'a') as f:
            for x,y in zip(a,b): 
                output = f"""rename network_objects {x} {y}\n"""
                f.write(output)

    mod_net(oldgwlist, newgwlist)
    mod_net(oldmemlist, newmemlist)

    # Verify changes with user
    print("\n[ Compiled dbedit file ]\n")
    os.system(f"cat {dbeditfile}")
    pause_script()

# reset sic on gateway side
def gw_sic_reset():

    print("\n[ Reset SIC on Gateway Side ]\n")

    for gw,newgw in zip(oldgwlist,newgwlist): 
        sicreset = f'{gwpath}/gw_rename_{gw}_sic_reset.sh'
        with open(sicreset, 'w') as f: 
                bashfile = f"""#!/bin/bash
. /etc/profile.d/CP.sh

clish -sc "set hostname {newgw}"
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


    for mem,newmem in zip(oldmemlist,newmemlist): 
        sicreset = f'{gwpath}/gw_rename_{mem}_sic_reset.sh'
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
    for gw,ip in zip(oldgwlist,gwiplist):
        sendsic = f'{gwpath}/gw_rename_{gw}_send_sic.sh'
        commands = f"""cprid_util -debug -server {ip} -verbose putfile -local_file "{gwpath}/gw_rename_{gw}_sic_reset.sh" -remote_file "/home/admin/{gw}_sic_reset.sh" -perms 700
cprid_util -debug -server {ip} -verbose rexec -rcmd /home/admin/{gw}_sic_reset.sh
"""
        bash_script(commands, sendsic)

        if debug == 1:
            print(commands)

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
    bash_script(commands, dbeditapply)
    
    # new gateway name list 
    cmd = f"""cpmiquerybin attr "" network_objects "(class='gateway_ckp')" -a __name__"""
    script = f'{gwpath}/gw_rename_oldgwlist.sh'
    new_oldgwlist = bash_script(cmd, script).split()

    # new gateway sic list 
    new_oldgwsiclist = []
    for sic in new_oldgwlist:
        cmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
        script = f'{gwpath}/gw_rename_oldgwsiclist.sh'
        oldgwsiclistnew = bash_script(cmd, script)
        new_oldgwsiclist.append(oldgwsiclistnew)

    print("\n[ CURRENT GATEWAY CONFIGURATION / SIC ]\n")
    print(f"\nNEW Cluster Members List\n{new_oldgwlist}\n")
    print(f"\nNEW SIC List\n{new_oldgwsiclist}\n")
    pause_script()


    #new cluster member name list
    cmd = """cpmiquerybin attr "" network_objects "(class='cluster_member')" -a __name__"""
    script = f'{gwpath}/gw_rename_newmemlist_2.txt'
    new_oldmemlist = bash_script(cmd, script).split()

    new_oldsiclist = []
    for sic in new_oldmemlist: 
        cmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
        script = f'{gwpath}/gw_rename_newsiclist_2.txt'
        oldsiclistnewnew = bash_script(cmd, script)
        new_oldsiclist.append(oldsiclistnewnew)

    print("\n[ CURRENT CLUSTER CONFIGURATION / SIC ]\n")
    print(f"\nNEW Cluster Members List\n{new_oldmemlist}\n")
    print(f"\nNEW SIC List\n{new_oldsiclist}\n")
    pause_script()


def api_sic(): 

    print("\n[ Establish SIC on API and update member names ]\n")

    

    # Update gateway name...
    for x,y in zip(oldgwlist, newgwlist):
        print(f"...Updating gateway name {x} to {y}\n")
        command = f"""mgmt_cli -s {cmasid} set simple-gateway name "{x}" ignore-warnings "true" new-name "{y}" one-time-password "vpn123" """

    publishsid = f'mgmt_cli publish -s {cmasid}'
    publishfile = f'{gwpath}/gw_rename_publishfile.sh'
    bash_script(publishsid, publishfile)
    
    #Update cluster object name...
    for x,y in zip(oldclulist, newclulist): 
        print(f"...Updating cluster object name {x} to {y}\n")
        command = f"""mgmt_cli -s {cmasid} set simple-cluster name "{x}" new-name "{y}" ignore-warnings "true" """
        bash_script(command, clurename)

    publishsid = f'mgmt_cli publish -s {cmasid}'
    publishfile = f'{gwpath}/gw_rename_publishfile.sh'
    bash_script(publishsid, publishfile)


    #update cluster member names 
    print("\n...Update Cluster Member Names and establish SIC ")

    command = f"""mgmt_cli -s {cmasid} set simple-cluster name "{newclulist[0]}" ignore-warnings "true" """

    for i,item in enumerate(newmemlist):
        print(f'FOR LOOP: {i}\n{item}\n{newmemlist}\n')
        command1 = f"""members.update.{i}.name "{item}" members.update.{i}.one-time-password "vpn123" """
        print(f'command1: {command1}\n')
        command = command + command1

    print(f'api_sic command:\n{command}')
    pause_script()

    bash_script(command, esic)
    timeout(1)


def end():
        logging.error(traceback.format_exec())
        print("[Logging user out]\n")
        logout(sid)
        command = f'mgmt_cli logout -s {cmasid}'
        script = f'{gwpath}/gw_rename_logout.sh'
        bash_script(command, script)
        sys.exit(0)


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

    # Create lists of cluster members, objects, and standard gateways 
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
        end()
    finally:
        end()
