from datetime import datetime
from flask import Flask, render_template, request, jsonify
from netmiko import ConnectHandler
import time
import pythonping
import os
from pymongo import MongoClient

app = Flask(__name__)

login = os.getenv("LOGIN")
password = os.getenv("PASSWORD")

#подключение в БД логов
#myclient = MongoClient("mongodb://10.0.10.219:27017/", username="root", password="example")
#db = myclient["log"]
#collection = db["log"]


#создание устройства
device = {
    'device_type': 'mikrotik_routeros',
    'username': login,
    'password': password,
    'port': 45000
}


#def write_log(*args,**kwargs):
   # collection.insert_many(*args,**kwargs)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_proxy', methods=['POST'])
def check_proxy():
    data = request.json
    number = data.get('number', 1)
    user = data.get('user', 1)

    device['host'] = f'192.168.{number}.1'

    try:
        with ConnectHandler(**device) as conn:
            output = conn.send_command_timing("ip proxy connections print")
           # write_log([{"event":"check_proxy","ip_admin":user,"number":number,"datetime":datetime.now()}])
            return output
    except Exception as e:
        return f'Failed to connect: {device["host"]}, because {e}'

@app.route('/restart_proxy', methods=['POST'])
def restart_proxy():
    data = request.json
    number = data.get('number', 1)
    user = data.get('user', 1)

    device['host'] = f'192.168.{number}.1'

    try:
        with ConnectHandler(**device) as conn:
            conn.send_command("ip proxy set enabled=no", strip_command=False, strip_prompt=False)
            time.sleep(1)
            conn.send_command("ip proxy set enabled=yes", strip_command=False, strip_prompt=False)
            time.sleep(1)
           # write_log([{"event":"restart_proxy","ip_admin":user,"number":number,"datetime":datetime.now()}])
            return f'Proxy restarted'
    except Exception as e:
        return f'Failed to connect: {device["host"]}'


@app.route('/change_lease', methods=['POST'])
def change_lease():
    data = request.json
    number = data.get('number', 1)
    user = data.get('user', 1)
    host_old = data.get('host_old', 1)
    host_new = data.get('host_new', 1)

    # Проверка списка запрещённых адресов
    allow_host = [11, 12, 13, 14, 15, 16, 17, 18, 19]
    if int(host_new) in allow_host and int(host_old) in (range(170,241)):
        pass
    else:
        return f'Адрес находится в списке запрещённых'

    # Проверка доступности адреса
    result = pythonping.ping(f'192.168.{number}.{host_new}')
    for response in result:
        if str(response) != "Request timed out":
            return "Этот адрес занят"

    device['host'] = f'192.168.{number}.1'

    try:
        with ConnectHandler(**device) as conn:
            output = conn.send_command(f"ip dhcp-server lease remove [find address=192.168.{number}.{host_new}]", strip_command=False, strip_prompt=False)
            output = conn.send_command(f"ip dhcp-server lease make-static [find address=192.168.{number}.{host_old}]", strip_command=False, strip_prompt=False)
            output = conn.send_command(f"ip dhcp-server lease set address=192.168.{number}.{host_new} [find address=192.168.{number}.{host_old}]", strip_command=False, strip_prompt=False)
           # write_log([{"event":"change","ip_admin":user,"number":number,"datetime":datetime.now()}])
            return 'Адрес заменён'
    except Exception as e:
        return f'Failed to connect: {device["host"]}'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
