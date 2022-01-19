import os
from os import path
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
gwpath = '/tmp/gw_rename_project'
log = f'{gwpath}/gw_rename_api.log'
cmasid = f'{gwpath}/gw_rename_sid.txt'
shell = '#!/bin/bash'
cpprofile = 'source /etc/profile.d/CP.sh'
dbeditfile = f'{gwpath}/gw_rename_{domain_name}.dbedit'
dbeditapply = f'{gwpath}/gw_rename_{domain_name}_dbedit_apply.sh'
mdsenv = f'mdsenv {cma_ip}'


#help menu
def helpmenu():
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
        print(
            '''
            \n[ Debug Mode Enabled ]\n
            '''
        ) 
        debugmode = 1
    else: 
        print("\n[ Debug Mode Disabled ]\n")
        debugmode = 0
    
    return debugmode
    

def askConfig():

    print("\n[ Provide Configuration ]\n")

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

    return username, password, domain_name, cma_ip, api_ip, api_port


# make code directory / clear log files 
def gw_mkdir(gwpath):

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
    input("[ DEBUG ] Press any key to continue")    


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
def login(username, password, domain, url, cmasid): 

    print("\n[ Login to API ]\n")

    defname = f"API : Login : {domain}"
    
    gw_url = f'{url}/login'
    headers = {'Content-Type' : 'application/json'}
    body = {'user' : f'{username}', 
            'password' : f'{password}',
            'domain' : f'{domain}'}

    api_post = requests.post(gw_url, data = json.dumps(body), headers=headers, verify=False)
    result = json.loads(api_post.text)

    response = api_post.status_code
    if response == 200: 
        print(f'\t {response}... Log in Successful.\n')
    else: 
        print(f'\t{response}... Login Failed.\n')


    sleeptime(1)
    api_debug(defname, url, headers, body, result, api_post)

    #write session id to OS for later use
    with open(cmasid, 'w') as f: 
        f.write(str(result))

    return result


# API Publish
def publish(url, domain, sid): 

    print("\n[ Publish Changes ]\n")

    defname = f"API : Publish : {domain}"

    gw_url = f'{url}/publish'
    x = sid["sid"]
    headers = {'Content-Type' : 'application/json',
                'X-chkp-sid' : f'{x}'} 
    body = {}
    api_post = requests.post(gw_url, data=json.dumps(body), headers=headers, verify=False)
    result = api_post.json() 

    response = api_post.status_code
    if response == 200: 
        print(f'\t {response}... Publish Successful.\n')
    else: 
        print(f'\t{response}... Publish Failed.\n')

    sleeptime(1)
    api_debug(defname, gw_url, headers, body, result, api_post)

    if len(sys.argv) > 1 and sys.argv[1] == "-d":
        with open (f'{domain}_publish.json', 'a') as f:
         f.write(json.dumps(result))


# API Logout
def logout(url, sid): 

    print("\n[ Log out of session ]\n")

    defname = f"API : Logout : {sid['sid']}"

    gw_url = f'{url}/logout'
    x = sid["sid"]
    headers = {'Content-Type' : 'application/json',
                'X-chkp-sid' : f'{x}'} 
    body = {}
    api_post = requests.post(gw_url, data=json.dumps(body), headers=headers, verify=False)
    result = api_post.json()

    response = api_post.status_code
    if response == 200: 
        print(f'\t {response}... Logged out\n')
    else: 
        print(f'\t{response}... Login failed\n')


    sleeptime(1)
    api_debug(defname, gw_url, headers, body, result, api_post)

# create scripts to run on mds
def bash_script(cmd, script, runfile):

    mdsbash=f"""
    {shell} 
    {cpprofile}

    {mdsenv}
    {cmd}\r 
    """
    script = f'{script}'
    with open(script, 'w') as f: 
        f.write(mdsbash)

    if runfile == 1:
        os.system(f"chmod +x {script}")
        runcmd = f"{script}"
        
        vallist = subprocess.check_output(runcmd, shell=True, text=True)

        print(f"\n{script}: {vallist}\n")

        return vallist


def gw_info(domain, ip, debug): 

    print("\n[ List GW and SIC Names / Convert Lists ]\n")

     # (oldmemlist) cluster member names list on CMA
    memcmd = """cpmiquerybin attr "" network_objects "(class='cluster_member')" -a __name__"""
    memscript = f'{gwpath}/gw_rename_oldmemlist.txt'
    oldmemlist = bash_script(memcmd, memscript, 0).split()
    
    # (cmiplist) cluster member IP addresses list on CMA
    cmiplist = []
    for cmname in oldmemlist:
        cmcmd = f"""cpmiquerybin attr "" network_objects "(name='{cmname}')" -a ipaddr | tr -d '[:space:]'"""
        cmscript = f'{gwpath}/gw_rename_cmiplist.txt'
        cmiplistnew = bash_script(cmcmd, cmscript, 0)
        cmiplist.append(cmiplistnew)

    # get SIC name of each cluster member
    oldsiclist = []
    for sic in oldmemlist: 
        siccmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
        sicscript = f'{gwpath}/gw_rename_oldsiclist.txt'
        oldsiclistnew = bash_script(siccmd, sicscript, 0)
        oldsiclist.append(oldsiclistnew)

    # debug 
    if debug == 1: 
        print(f"Old Cluster Members List\n{oldmemlist}\n")
        print(f"Cluster Member IP List: {cmiplist}\n")
        print(f"Old SIC List\n{oldsiclist}\n")
        pause_debug()
    
    return cmiplist, oldmemlist, oldsiclist


def dbeditcreate(domain, debug):

    # (newmemlist) Ask user for new name of each cluster member 
    newmemlist = []
    for mem in oldmemlist:
        newmem = input(f"Type new name for {mem}: ")
        newmemlist.append(newmem)

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
            output = f"""\nmodify network_objects {x} sic_name "{y}"\n"""
            f.write(output)

    # Update old network object name with new name 
    with open(dbeditfile, 'a') as f:
        for x,y in zip(oldmemlist,newmemlist): 
            output = f"""\nrename network_objects {x} {y}\n"""
            f.write(output)

    with open(dbeditfile, 'a') as f: 
        output = "\nquit -update_all\n"
        f.write(output)

    # debug 
    if debug == 1: 
        print("\n[Compiled dbedit file]\n")
        os.system(f"cat {dbeditfile}")
        pause_debug()


    return newmemlist, newsiclist


def gw_sic_reset(oldnamelist, newnamelist, iplist, debug):

    print("\n[ Reset SIC on Gateway Side ]\n")

    for member,newmem in zip(oldnamelist,newnamelist): 
        with open(f'{gwpath}/gw_rename_{member}_sic_reset.sh', 'w') as f: 
                bashfile = f"""
    #!/bin/bash
    . /etc/profile.d/CP.sh
    clish -sc "set hostname {newmem}"
    cp_conf sic init vpn123 norestart
    cpwd_admin stop -name CPD -path "\$CPDIR/bin/cpd_admin" -command "cpd_admin stop" >/home/admin/cpdstop
    cpwd_admin start -name CPD -path "\$CPDIR/bin/cpd" -command "cpd" > /home/admin/cpdstart
    FAIL="\$(cat /home/admin/cpdstart | grep "CPD is alive")"
    SUCCESS="\$(cat /home/admin/cpdstart | grep "Process CPD started successfully")"
    if [ -n "\$SUCCESS" ]
    then
        echo "SUCCESS"
    else
        if [ -n "\$FAIL" ]
        then
            echo "FAILURE"
        fi
    fi"""
                f.write(bashfile)           

    
    # send bash file to gateway and execute sic reset

    commands = f"""
    cprid_util -server {ip} -verbose putfile -local_file {member}_sic_reset.sh -remote_file /home/admin/{member}_sic_reset.sh
    cprid_util -server {ip} -verbose rexec -rcmd chmod 700 /home/admin/{member}_sic_reset.sh
    cprid_util -server {ip} -verbose rexec -rcmd /home/admin/{member}_sic_reset.sh
    """

    sendsic = f'{gwpath}/gw_rename_{member}_send_sic.sh'

    for member,ip in zip(oldnamelist,iplist):
        bash_script(commands, sendsic, 1)

        if debug == 1:
            print(commands)


def dbedit_apply(cmaip, debug): 

    print("\n[ Apply dbedit configuration to CMA ]\n")

    commands= f"""
    dbedit -local -f {dbeditfile}
    """

    bash_script(commands, dbeditapply, 1)

    if debug == 1: 
        print("[ New Configuration Hostname / SIC ]")

        memcmd = """cpmiquerybin attr "" network_objects "(class='cluster_member')" -a __name__"""
        memscript = f'{gwpath}/gw_rename_newmemlist_2.txt'
        oldmemlist = bash_script(memcmd, memscript, 0).split()

        oldsiclist = []
        for sic in oldmemlist: 
            siccmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
            sicscript = f'{gwpath}/gw_rename_newsiclist_2.txt'
            oldsiclistnew = bash_script(siccmd, sicscript, 0)
            oldsiclist.append(oldsiclistnew)

        print(f"Old Cluster Members List\n{oldmemlist}\n")
        print(f"Old SIC List\n{oldsiclist}\n")
        pause_debug()


def api_sic(cmaip, newnamelist, sid, debug): 

    print("\n[ Establish SIC on API and update member names ]\n")

    clulist = f'{gwpath}/gw_rename_clulist.txt'

    commands = """`cpmiquerybin attr "" network_objects "(class='gateway_cluster')" -a __name__`"""
    clulistnew = bash_script(commands, clulist, 0).split()

    if debug == 1: 
        print(f'clulist:\n {clulistnew}')
        pause_debug()

    esic = f'{gwpath}/gw_rename_establishsic.sh'

    command1 = f"""mgmt_cli -s {gwsid} \ \n"""
    command2 = f"""set simple-cluster name "{clulist[0]}" ignore-warnings "true" \ \n"""
    
    with open(esic, 'a') as f:
        f.write(command1)
        f.write(command2)
        for i,item in enumerate(newnamelist):
            command3 = f"""
            members.update.{i}.name "{item}" \
            members.update.{i}.one-time-password "vpn123" \ \n 
            """
            f.write(command3)
 

    bash_script(commands, esic, 1)

    if debug == 1:
        with open(esic, 'r') as f:
            f.read()
        
        pause_debug()

    publish(sid)
   


def main(): 

    debugmode = helpmenu()

    username, password, domain_name, cma_ip, api_ip, api_port = askConfig()

    #global url variable, import local config file
    url = f'https://{api_ip}:{api_port}/web_api'
    print(f"\n[ Global URL Variable]\n{url}\n")

    

    # create new log directory, delete old log files
    gw_mkdir(gwpath)

    #login to domain 
    sid = login(username, password, domain_name, url)

    # get list of CMA's and CMA IP's from system 
    cmiplist, oldmemlist, oldsiclist = gw_info(domain_name, cma_ip, debugmode)

    # create dbedit file
    newmemlist, newsiclist = dbeditcreate(domain, debugmode)
    
    # create bash file and send to gateways to reset sic 
    gw_sic_reset(oldmemlist, newmemlist, cmiplist, debugmode)

    # apply dbedit change 
    dbedit_apply(cma_ip, debugmode)

    # apply api changes to establish sic
    api_sic(cma_ip, newmemlist, debugmode)

    # publish changes 
    publish(url, domain_name, sid)

    # logout of session
    logout(url, sid)


if __name__=="__main__":
    try:
        main()
    except Exception as e:
        logging.error(traceback.format_exec())
        print("[Logging user out]\n")
        logout(url, sid)
        sys.exit(0)
        os._exit(0)
    finally:
        print("[Logging user out]\n")
        logout(url, sid)
        sys.exit(0)
        os._exit(0)
