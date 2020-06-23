from jnpr.junos import Device
from jnpr.junos.factory.factory_loader import FactoryLoader
from influxdb import InfluxDBClient
import yaml

host = 'x.x.x.x'
port = 'port_number'
user = '<uname>'
password = '<pwd>'
dbname = '<db_name>'

yaml_data = """
---
McastSourceList:
    rpc: get-multicast-usage-information
    args:
      detail: True
    item: multicast-group
    key: multicast-group-address
    view: McastSourceView

McastSourceView:
    fields:
      group-packet-count: multicast-packet-count
      group-byte-count: multicast-byte-count
      multicast-group-address: multicast-group-address
      multicast-source-count: multicast-source-count
      multicast-source-address: multicast-group-source/multicast-source-address
"""


dev = Device(host='x.x.x.x', user='<dev uname>', password='<dev pwd>', gather_facts=False)
dev.open()

globals().update(FactoryLoader().load(yaml.load(yaml_data)))
mcgrps = McastSourceList(dev)
print (mcgrps.get())
dev.close()

def create_multicast_grp_configs_sot(host, port, user, password, dbname):
    client = InfluxDBClient(host, port, user, password, dbname)
    grp_configs = [{"measurement":"msrmt_grp_configs",
            "tags": {
                "DeviceIP": "<dev ip>"
            },
            "fields":
            {
                "Configs": "{'x.x.x.1':(2, ['y.y.y.y', 'y.y.y.y']) , 'x.x.x.2':(1,['y.y.y.y'])}"
            }}]

    client.create_database('test_mohan')
    client.write_points(grp_configs)
