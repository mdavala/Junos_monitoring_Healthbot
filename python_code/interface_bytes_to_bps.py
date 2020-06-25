from __future__ import division
from __future__ import print_function
import sys
import copy
import pprint
import requests

prev_value = {}
prev_time = {}
prev_bps = {}

ns_server = 'X.X.X.X'
ns_port = 'xxxx'
ns_headers = {'Authorization': 'Bearer 4E6sdoZ0c4pyMi41xaGLqsajS+WmfGY6gG8dhWMQBh4='}
ns_api = 'https://{}:{}/NorthStar/API/v2/tenant/1/topology/1/links/11'.format(ns_server, ns_port)


mx_delays = {'DN1':0, 'RN001':0}

'''
This function returns the delta of the counter between current and previous values
'''
def interface_bytes_to_bps(direction, index_name, bytes_counter='', **kwargs):
    global prev_value
    global prev_time
    global prev_bps
    
    #print ("[mdavala] kwargs: {}".format(kwargs))
    index_name_direction = index_name + "-" + direction
    
    if bytes_counter=='':
        bps = 0
        return bps

    #print ("[mdavala] if_name direction {}".format(index_name_direction))
    cur_time = kwargs.get('point_time', 0)
    bytes_counter = int(bytes_counter)

    # convert bytes into bits
    # bps = (bytes * 8)
    bits_counter = bytes_counter * 8
    cur_value = bits_counter
    #print ("[mdavala] cur value {}".format(cur_value))

    # calculate the time difference
    time_difference = ( cur_time - prev_time.get(index_name_direction, 0) )

    if (time_difference == 0):
        print('__ERROR__ avoiding division by zero')

        # return zero to avoid division by zero
        return 0
    else:
        # Calculate data seen in bps
        try:
            bps = abs( cur_value - prev_value.get(index_name_direction, 0) ) / time_difference
        except Exception:
            print("error: exception caught!", file=sys.stderr)
            bps = prev_value.get(index_name_direction, 0)

        # update global variables
        prev_value[index_name_direction] = cur_value
        prev_time[index_name_direction] = cur_time

        #kbps = bps/1024
        #usage_percentage = (kbps/total_bw_capacity) * 100
        #mbps = kbps/1000
        #print ("[mdavala] returning bps {}".format(bps)) 
        return abs(bps)

def juniper_bps_percentage(if_name, bps, **kwargs):
    gbps = bps/(10**9)
    if 'et-' in if_name:
        if if_name == 'et-1/0/11':
            #print ("[mdavala] exception interface with 40G")
            pcnt = gbps * 2.5
            #print ("[mdavala] if_name {} = pcnt {}".format(if_name, pcnt))
            return round(pcnt)       
        else:
            #print ("[mdavala] exception interface with 100G")
            pcnt = gbps
            #print ("[mdavala] if_name {} = pcnt {}".format(if_name, pcnt))
            return round(pcnt)
    elif 'xe-' in if_name:
        #print ("[mdavala] exception interface with 10G")
        pcnt = gbps * 10
        #print ("[mdavala] if_name {} = pcnt {}".format(if_name, pcnt))
        return round(pcnt)
    elif 'ge-' in if_name:
        #print ("[mdavala] exception interface with 1G")
        pcnt = gbps * 100
        #print ("[mdavala] if_name {} = pcnt {}".format(if_name, pcnt))
        return round(pcnt)
    else:
        #print ("[mdavala] error: no interface found in any conditions {}".format(if_name))
        return -1

def do_ns_rest_call(max_delay, twamp_owner, **kwargs):
    #print ("[mdavala] kwargs: {}".format(kwargs))
    #print ("[mdavala] max_delay: {}".format(max_delay))
    #print ("[mdavala] session_name: {}".format(twamp_owner))
    #print ("[mdavala] {}".format(ns_api))

    if kwargs.get('device_id') == 'DN2' and twamp_owner=="dn2-client-dn1":
        mx_delays[kwargs.get('device_id')] = int(max_delay/2)
        #print ("[mdavala] updated cpe delays {} {}".format(kwargs.get('device_id'), mx_delays))
        r = requests.get(ns_api, headers=ns_headers, verify=False)
        if r.status_code == 200:
            data = r.json()
            #print ("[mdavala] data: {}".format(data))
            del data['endA']['protocols']['ISIS']['metric']
            del data['endA']['protocols']['ISIS']['metricL1']
            del data['endZ']['protocols']['ISIS']['metric']
            del data['endZ']['protocols']['ISIS']['metricL1']
            data['endA']['delay'] = mx_delays[kwargs.get('device_id')]
            data['endZ']['delay'] = mx_delays[kwargs.get('device_id')]
            #print ("[mdavala] updated data {}".format(data))
            p = requests.put(ns_api, headers=ns_headers, json=data, verify=False)
            
            #print ("[mdavala] put content: {}".format(p.content))
            if p.status_code == 200:
                #print ("[mdavala] API_UPDATE_CALL_SUCCESS")
                return "API_UPDATE_CALL_SUCCESS: {}".format(p.status_code)
            else:
                #print ("[mdavala] API_UPDATE_CALL_FAILED")
                return "API_UPDATE_CALL_FAILED: {}".format(p.status_code)
        else:
            #print ("[mdavala] API_GET_CALL_FAILED")
            return "API_GET_CALL_FAILED {}".format(r.status_code)

