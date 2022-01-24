import ipaddress
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

#remove insecure https warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

###Functions to build working environment###
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

#input validation
def question(stuff):
    while True:
        answer = input(f"\n{stuff}: ")
        if len(answer) is not 0:
            False
            return answer 

#configuration for api/login/domain/cma
def askConfig():

    print("\n[ Provide API/CMA/Domain Configuration ]\n")

    global username, password, domain_name, cma_ip, api_ip, api_port

    username = question("Username")
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

# make log directory / clear old log files
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


###Debugging Functions###
# take any input to pause debug 
def pause_debug():
    input("[ DEBUG ] Press any key to continue...\n\n")   

def pause_script():
    input("\n\n--- Check and Verify. Press any key to continue ---") 


###API Functions###
# log api responses/information
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
            'domain' : f'{domain}',
            'session-timeout' : 1800}

    api_post = requests.post(api_url, data = json.dumps(body), headers=headers, verify=False)
    result = json.loads(api_post.text)

    global domain_sid
    domain_sid = result

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    response = api_post.status_code
    if response == 200: 
        print(f'{response}... Log in Successful.\n')
    else: 
        print(f'{response}... Login Failed.\n')

    global file_sid
    file_sid = f'{gwpath}/gw_rename_sid.txt'
    with open(file_sid, 'w') as f:
        f.write(api_post.text)

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


###List Gateways, Clusters, Cluster Members###
def show_simple(config, domain, sid):

    print(f"\n[ API : Generate Cluster Object List : {domain}]\n")
    defname = f"API : Show Simple Gateways : {domain}"
    
    api_url = f'{url}/show-simple-{config}'
    x = sid["sid"]
    headers = {'Content-Type' : 'application/json',
                'X-chkp-sid' : f'{x}'} 
    body = {}

    api_post = requests.post(api_url, data=json.dumps(body), headers=headers, verify=False)
    result = api_post.json()

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    if config == 'gateways':
        global gatewaylist
        gatewaylist = [] 
        for gw in result['objects']:
            gatewaylist.append(gw['name'])
        
        print(f"[ API: GATEWAY LIST ]\n{gatewaylist}\n")

    if config == 'clusters':
        global clusterlist
        clusterlist = [] 
        for i in result['objects']:
            clusterlist.append(i['name'])
    
        print(f"[ API: CLUSTER OBJECT LIST ]\n{clusterlist}\n")



#only called, if the answer is a cluster object
def members(cluster, domain, sid):

    print(f"\n[ API: Generate Cluster Member List : {domain}]\n")
    defname = f"API : Show Cluster Members : {domain}"
    
    api_url = f'{url}/show-simple-cluster'
    x = sid["sid"]
    headers = {'Content-Type' : 'application/json',
                'X-chkp-sid' : f'{x}'} 
    body = {'name' : f'{cluster}'}

    api_post = requests.post(api_url, data=json.dumps(body), headers=headers, verify=False)
    result = api_post.json()

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)
    
    global memberlist
    memberlist = [] 
    for i in result['cluster-members']:
        memberlist.append(i['name'])

    print(f"[ API: CLUSTER MEMBER LIST ]\n{memberlist}\n")


#leverage api to build connected list of cluster object/members
#Build Dictionary with lists to have something to easily iterate through
def cluster_member_link(cluster):
    global linkedlist
    linkedlist = {}
    members(cluster, domain_name, domain_sid)
    for m in memberlist:
        linkedlist.setdefault(cluster, []).append(m)

    print(f"\n[ Linked List ]\n{linkedlist}\n")


def info(config, name, sid):
    
    print(f"\n[ API: show-simple-{config} : {name}]\n")
    defname = f"API : show-simple-{config} : {name}"
    
    api_url = f'{url}/show-simple-{config}'
    x = sid["sid"]
    headers = {'Content-Type' : 'application/json',
                'X-chkp-sid' : f'{x}'} 
    body = {'name' : f'{name}',
            'details-level' : 'full'}

    api_post = requests.post(api_url, data=json.dumps(body), headers=headers, verify=False)
    result = json.loads(api_post.text)

    sleeptime(1)
    api_debug(defname, api_url, headers, body, result, api_post)

    return result


### Ask user what object to change the name of ###

def start_menu():
    list = gatewaylist + clusterlist
    menu = '\n'
    for i,k in enumerate(list):
        menu += f'{i} : {k}\n'
    answer = question(f"{menu}\nEnter name of object to edit\n")

    if answer in list:
        return answer
    else:
        start_menu()
    
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

    print(f"[ RESULT ]\n{vallist}\n\n")

    return vallist


# reset sic on gateway side
def sic_reset(oldname, newname, ip):

    print("\n[ Reset SIC on Gateway Side ]\n")

    filename = f'{gwpath}/gw_rename_{oldname}_sic_reset.sh'
    with open(filename, 'w') as f: 
        bashfile = f"""#!/bin/bash
. /etc/profile.d/CP.sh

clish -sc "set hostname {newname}"
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
    print(f'[ RESETTING SIC... {oldname} ]\n')
    cmd = f"""cprid_util -debug -server {ip} -verbose putfile -local_file "{filename}" -remote_file "/home/admin/gw_rename_{oldname}_sic_reset.sh" -perms 700
cprid_util -debug -server {ip} -verbose rexec -rcmd /home/admin/gw_rename_{oldname}_sic_reset.sh
"""
    filename = f'{gwpath}/gw_rename_{oldname}_send_sic.sh'
    bash_script(cmd, filename)

    if debug == 1:
        print(cmd)


def api_sic_gw(oldname, newname): 

    print("\n[ SIC: Management -> Gateway ]\n")
    print(f"...Updating gateway name {oldname} to {newname}\n")

    cmd = f"""mgmt_cli -s {file_sid} set simple-gateway name "{oldname}" new-name "{newname}" one-time-password "vpn123" """
    filename = f'{gwpath}/gw_rename_{oldname}_to_{newname}.sh'

    bash_script(cmd, filename)
    publish(domain_name, domain_sid)


def api_sic_cluster(oldname, newname, members):

    print("\n[ SIC: Management -> Cluster ]\n")
    print(f"...Updating cluster object name {oldname} to {newname}\n")

    cmd = f"""mgmt_cli -s {domain_sid} set simple-cluster name "{oldname}" new-name "{newname}" members.update.0.name "{members[0]}" members.update.0.one-time-password "vpn123" members.update.1.name "{members[0]}" members.update.1.one-time-password "vpn123" """
    filename = f'{gwpath}/gw_rename_{oldname}_to_{newname}.sh'

    bash_script(cmd, filename)
    publish(domain_name, domain_sid)




def dbeditcreate(name):

    print('\n[ Dbedit File Create ]\n')

    # get the result of sic name from dbedit
    cmd = f"""cpmiquerybin attr "" network_objects "(name='{sic}')" -a sic_name | tr -d '[:space:]'"""
    script = f'{gwpath}/gw_rename_sic_name_{sic}.sh'
    oldgwsiclistnew = bash_script(cmd, script)
    oldgwsiclist.append(oldgwsiclistnew)

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


### Make dbedit file ###
# Modify SIC entries 
def mod_sic(a, b):
    with open(dbeditfile, 'a') as f:
        for x,y in zip(a, b):
            output = f"""modify network_objects {x} sic_name "{y}"\n"""
            f.write(output)

# Modify network object names
def mod_net(a, b):
    with open(dbeditfile, 'a') as f:
        for x,y in zip(a,b): 
            output = f"""rename network_objects {x} {y}\n"""
            f.write(output)

#add gateway dbedit config



def dbedit_apply(): 

    print("\n[ Apply dbedit configuration to CMA ]\n")

    dbeditfile = f'{gwpath}/gw_rename_dbedit.dbedit'
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


    
###Gateway Class Object###
#Need to get rid of list iteration
class Gateway:
    def __init__(self, name):
        self.name = name 
        self.ipadd = ''
        self.newname = ''
        self.oldsic = ''
        self.newsic = ''

    # Store IP Address from API
    def gw_ip(self):
        print(f"\n Class Gateway: IP Address\n")
        result = info('gateway', self.name, domain_sid)
        self.ipadd = result['ipv4-address']
        
    def gw_oldsic(self):
        cmd = f"""cpmiquerybin attr "" network_objects "(name='{self.name}')" -a sic_name | tr -d '[:space:]'"""
        script = f'{gwpath}/gw_rename_sic_name_{self.name}.sh'
        self.oldsic = bash_script(cmd, script)

    # new name of gateway
    def gw_newname(self):
        answer = question(f"Enter new name for gateway {self.name}")
        self.newname = answer
    
    # create new sic name
    def gw_newsic(self):
        self.newsic = self.oldsic.replace(self.newname)

    # add gateway dbedit config 
    def gw_dbedit(self):
        mod_sic(self.name, self.newsic)
        mod_net(self.name, self.newname)

    
    # Reset SIC on gateway side 
    def gw_sicreset(self):
        sic_reset(self.name, self.newname, self.ipadd)

    # Update SIC on management side 
    def gw_apisic(self):
        api_sic_gw(self.name, self.newname)
        

class Cluster:
    def __init__(self, name):
        self.name = name
        self.cmip = ''
        self.newname = ''
        self.newmem = ''
        self.newsic = ''

    # New name of cluster object
    def cl_newname(self):
        self.newname = question(f"Enter new name for cluster{self.name}")

    # New names for cluster members
    def cm_newmame(self):
        self.newmem = []
        for mem in memberlist:
            answer = question(f"Enter new name for cluster member {mem}")
            self.newmem.append(answer)

    # From api result, get IP address list of cluster members
    def cm_ip(self):
        self.ipadd = []
        result = info(self.name, 'cluster', domain_sid)
        for mem in result['cluster-members']:
            self.ipadd.append(mem['ip-address'])

    #add cluster member dbedit config
    mod_sic(self.mem, self.newsic)
    mod_net(self.mem, self.newmem)

    # Reset SIC on gateway side 
    def cm_sicreset(self):
        for x,y in zip(memberlist, self.newmem):
            sic_reset(x, y, self.ipadd)

    # Update Cluster Name/SIC on management side 
    def cl_apisic(self):
        api_sic_cluster(self.name, self.newname)


def end():
        logout(domain_sid)
        sys.exit(0)


def main(): 

    #Global Variables
    global shell
    shell = '#!/bin/bash'
    global cpprofile
    cpprofile = 'source /etc/profile.d/CP.sh'
    global gwpath
    gwpath = '/tmp/gw_rename_project'
    global log
    log = f'{gwpath}/gw_rename_api.log'

    # if user adds arugment with -d or -h
    helpmenu()

    # get config from user for environment
    askConfig()

    #global url variable, import local config file
    global url
    url = f'https://{api_ip}:{api_port}/web_api'
    print(f"\n[ Global URL Variable]\n{url}\n")
    global mdsenv
    mdsenv = f'mdsenv {cma_ip}'
    
    # create new log directory, delete old log files
    gw_mkdir()

    #login to domain 
    login(domain_name)

    # get gateways and cluster lists from domain / API
    show_simple('gateways', domain_name, domain_sid)
    show_simple('clusters', domain_name, domain_sid)

    ### Ask the user which object we would like to edit###
    answer = start_menu()

    if answer in gatewaylist:
        gw = Gateway(answer)
        gw.gw_ip()
        gw.gw_newname()
        gw.gw_sicreset()
        gw.gw_apisic()

    elif answer in clusterlist:
        cluster_member_link(answer)
        cl = Cluster(answer)
        cl.cl_newname()
        cl.cm_newname()
        global newlinkedlist
        newlinkedlist = {}
        for m in cl.newmem:
            newlinkedlist.setdefault(cl.newname, []).append(m)
        print(f"\n[ New Linked List ]\n{newlinkedlist}\n")
        cl.cm_ip()

    else:
        print(f"[ EXITING...Contact Owner ]\n{answer}\n")
        end()
    
    

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"[ Error ]\n{e}\n")
    finally:
        end()
