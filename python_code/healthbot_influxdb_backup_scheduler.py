import subprocess, os
import time
#import pandas as pd
import paramiko, yaml
import smtplib
from email.mime.text import MIMEText
from scp import SCPClient
import datetime, time

# Parsing static yaml files (for now, we may change it in future by taking data dynamically from influxdb)

my_env = os.environ.copy()
def parseyaml(filename):
    with open(filename, 'r') as s:
        try:
            return (yaml.safe_load(s))
        except yaml.YAMLError as esc:
            logging.error (esc)
details = parseyaml('hb_backup_scheduler.yml')
#print ("details {}".format(details))

sender = details['sender']
receiver = details['receiver']

def get_storage_usage():
    hb_storage = subprocess.run(['df', '-h'], env=my_env, stdout=subprocess.PIPE).stdout.decode('utf-8')
    # Convert this into pandas dataframe for ease of use
    hb_df = []
    hb_storage = hb_storage.split('\n')
    for i, j in enumerate(hb_storage):
        hb_df.append(list(filter(None, j.split(' '))))
    # Merging 6th and 7th column being its single word (as Mountedon)
    hb_df[0][5] = ''.join(hb_df[0][5:7])
    del(hb_df[0][6])
    df = pd.DataFrame(hb_df[1:], columns= hb_df[0])
    df.set_index(df.columns[0], inplace=True)
    usage = df.loc['/dev/sda2']['Use%']
    print ("usage {}".format(usage))
    return (usage)

def createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

def send_email(sender, receiver, password, usage, hb_status):
    content = """This is CRITICAL MESSAGE from healthbot, storage reached {}%""".format(usage)
    content += """I stopped the healthbot, Below is the healthbot status \n {} """.format(hb_status)
    msg = MIMEText(content)
    msg['From'] = sender
    msg['To'] = ', '.join(receiver)
    msg['Subject'] = 'HEALTHBOT STORAGE EXCEEDED - CRITICAL'
    smtp_server_name = 'smtp.gmail.com'
    #port = '465' # for secure messages
    port = '587' # for normal messages

    if port == '465':
        server = smtplib.SMTP_SSL('{}:{}'.format(smtp_server_name, port))
    else :
        server = smtplib.SMTP('{}:{}'.format(smtp_server_name, port))
        server.starttls() # this is for secure reason

    server.login(user=sender, password=password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()

def get_filename(db, msrmt):
    msrmt = msrmt.replace('/', '_')
    csv_filename = db+'_'+msrmt+'_'+str(datetime.datetime.now().isoformat())+'.csv'
    print ("csv_filename {}".format(csv_filename))
    return csv_filename

def backup_influx():
    db_user = details['influxDB']['username']
    db_pwd = details['influxDB']['password']
    db_details = details['influxDB']['database']
    dbs = db_details.keys()

    print ("dbs: {}".format(dbs))
    for db in dbs:
        print ("db: {}".format(db))
        for msrmt in db_details[db]:
            print ("measurement {}".format(msrmt))
            csv_file = get_filename(db, msrmt)
            cli = "influx -username {} -password \"{}\" -database '{}' -host 'localhost' -execute 'SELECT * FROM \"{}\".\"{}\".\"{}\" where time > now() -1d order by time desc' -format 'csv' > {}".format(db_user, db_pwd, db, db, db, msrmt, csv_file)
            print ("influx cli {}".format(cli))       
            #exec_influx = subprocess.run([cli], stdout=subprocess.PIPE).stdout.decode('utf-8')
            exec_influx = os.system(cli)
            
            #scp_cli = 'scp {} -P 13022 root@203.209.87.51:/root/hb_backup/.'.format(csv_file) 
            ssh = createSSHClient(details['dest']['server'], details['dest']['port'], details['dest']['user'], details['dest']['password'])
            scp = SCPClient(ssh.get_transport())
            scp.put('/home/juniper/'+str(csv_file), details['dest']['path'])
            ssh.close()
            os.remove(csv_file)

    return "Success"
       

def job():
    #usage = get_storage_usage().replace('%', '')
    #Get current healthbot timestamp
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    print ("Healthbot timestamp {}".format(st))
    usage = 63
    print ("healthbot storage {}".format(usage))
    print ("healthbot pwd {}".format(os.getcwd()))
    if int(usage) >= 90:
        ssh = createSSHClient(details['dest']['server'], details['dest']['port'], details['dest']['user'], details['dest']['password'])
        scp = SCPClient(ssh.get_transport())
        scp.put(details['source_path'], details['dest']['path'])
        ssh.close()
        hb_status = subprocess.run(['healthbot', 'status'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    
        print ("hb_status {}".format(hb_status))
        send_email(details['sender'], details['receiver'], details['sender_password'], usage, hb_status)
        print ("Mail sent")

    if datetime.datetime.now().hour == 00 and datetime.datetime.now().minute == 00: 
        print ("Healthbot storage is good and taking regular backup at 00:00")
        ssh = createSSHClient(details['dest']['server'], details['dest']['port'], details['dest']['user'], details['dest']['password'])
        scp = SCPClient(ssh.get_transport())
        scp.put(details['source_path'], details['dest']['path'])
        ssh.close()
        res = backup_influx()

if __name__ == '__main__':
    job()

#schedule.every().day.at("00:00").do(job, "It is time to day's healthbot config backup")
#schedule.every(1).minutes.do(job, "It is time to backup today's healthbot configs")

#while True:
#    schedule.run_pending()
#    time.sleep(60)
