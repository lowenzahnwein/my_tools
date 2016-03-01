#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from httplib2 import Http
import datetime
import re
import sys

try:
    import simplejson as json
except ImportError:
    import json

def get_domain(url):
    scheme = url.find("://")
    if scheme != -1:
        url = url[scheme + 3:]
    if url.startswith("www."):
        url = url[4:]
    url = url.replace("/", "")
    return url

def remove_chars(str):
    str = re.sub("[(),.:;/&']", " ", str, 0, 0)
    str = re.sub(r'\s+', ' ', str)
    return str

def check_owner(first, second):
    if (first.lower() in second.lower()) or (second.lower() in first.lower()):
       return True
    first = remove_chars(first).lower()
    second = remove_chars(second).lower()
    intersection = (set(first.split()) & set(second.split()))
    if not intersection:
        return False
    else:
        return True
   
def check_by_whois(domain, name):
    http_obj = Http()
    resp, content = http_obj.request("http://tr-3.kaspersky-labs.com:3421/" + domain)
    assert resp.status == 200
    assert resp['content-type'] == 'text/html; charset=UTF-8'
    txt = content.decode("utf-8", "replace")
    info = json.loads(txt)
    result = {
        "status" : "",
        "domain" : domain,
        "messages" : []}
    if not info:
       result["status"] = "WARN"
       result["messages"].append("Unknown error") 
    elif 'error' in info:
       result["status"] = "ERROR"
       result["messages"].append(info["error"])
    else:
        if 'paidtill' in info:
            now = datetime.datetime.now()
            paidtill = datetime.datetime.strptime(info["paidtill"], "%Y-%m-%d")
            if now > paidtill:
                result["status"] = "ERROR"
                result["messages"].append("Bad paidtill date") 
        else:
           result["status"] = "WARN";
           result["messages"].append("Unknown paidtill")
        if 'owner' in info:
            owner = info['owner']
            if type(owner) is str:
                if check_owner(owner, name):
                    result["status"] = "OK"
                else:
                    result["status"] = "DISPUTED"
                    result["messages"].append(name + " <=> " + owner)
            elif type(owner) is list:
                is_checked = False
                for o in owner:
                    if check_owner(o, name):
                        is_checked = True
                        result["status"] = "OK"
                        break
                if not is_checked:
                    result["status"] = "DISPUTED"
                    result["messages"].append(name + " <=> " + ';'.join(owner))
            else:
               result["status"] = "ERROR"
               result["messages"].append("Invalid owner type")                                    
        else:
           result["status"] = "WARN";
           result["messages"].append("Unknown owner")       
        return result
    
def get_txt_info(url):
    http_obj = Http()
    resp, content = http_obj.request(url)
    assert resp.status == 200
    assert resp['content-type'] == 'text/plain'
    txt = content.decode() 
    list = txt.split('\n')
    list.remove('');
    return list

def get_orgs(types):
    str_list = get_txt_info("http://aphishdev.avp.ru:3000/orgs/orgsdb")
    orgs = {}
    for i, str in enumerate(str_list):
        if i % 2 == 0:
            first_space = str.index(' ')
            second_space = str.index(' ', first_space + 1)
            id = int(str[:first_space])
            type = int(str[first_space + 1:second_space])
            name = str[second_space + 1:]
            if type in types:
                orgs[id] = name
    return orgs

def check_domains(orgs):
    str_list = get_txt_info("http://aphishdev.avp.ru:3000/orgs/txturls")
    result = []
    debug = 0
    for str in str_list:
        if debug > 1000:
            break
        last_space = str.rindex(' ')
        penultimate_space = str.rindex(' ', 0, last_space)
        id = int(str[last_space + 1:])
        domain  = str[penultimate_space + 1:last_space]
        if id in orgs:
            try:
                info = check_by_whois(get_domain(domain), orgs[id])
                result.append(info)
                debug =+ 1
            except:
                print ("Error: ", sys.exc_info()[0])
    return json.dumps(result, ensure_ascii=False, indent=4, sort_keys=True)
        
def main():
    types = [0, 12]
    orgs = get_orgs(types)
    domains = check_domains(orgs)
    print (domains)
           
if __name__ == "__main__":
    main()


