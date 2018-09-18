## Install Docker
```
curl -fsSL get.docker.com -o get-docker.sh
sudo sh get-docker.sh

sudo usermod -aG docker `whoami`
#sudo apt-get install docker-compose
```
Remember to restart your terminal session to activate the new group.

## Install TIG Suite (Telegraf-InfluxDB-Grafana)

### from https://github.com/samuelebistoletti/docker-statsd-influxdb-grafana
https://hub.docker.com/r/samuelebistoletti/docker-statsd-influxdb-grafana/

Start with source on github and modify for Arm images instead of AMD. See
```docker-statsd-influxdb-grafana/Dockerfile``` for details.

We want the collected sensor data to hang around even if we stop the instance from running. The best way to do this is use the Docker Volume storage service.

#### Add SD Card for storing Influx Database
Format the SD Card.
```
sudo umount /dev/sda1
sudo fdisk /dev/sda
# 'n' then 'p', '1', 'default', default', default' to add new partition.
# 't' then '83' to change the partition type to linux, then 'w' to save.
sudo mkfs.ext4 -m 0 -L tagstore /dev/sda1
```
Create the location where we will mount the SD Card filesystem.
```
sudo mkdir /mnt/sdcard
sudo chown -c pi:devgrp /mnt/sdcard
chmod 775 /mnt/sdcard
```
Add this line to ```/etc/fstab``` to automatically mount the ```/mnt/sdcard``` filesystem on system boot.
```
/dev/sda1      /mnt/sdcard      ext4      rw,suid,dev,noexec,auto,user,async      0  0
```
To start it manually, use:
```
sudo mount -a
```

#### Create persistent Docker Volume on SD Card
```
mkdir /mnt/sdcard/influxdatabase
sudo ln -s /mnt/sdcard/influxdatabase /var/lib/docker/volumes/influxdatabase
docker volume create --name influxdatabase
```

#### Build Docker Image with:
```
docker build -t docker-statsd-influxdb-grafana .
```

#### Versions
```
#Docker Image: 2.1.0
Ubuntu: 16.04
InfluxDB: 1.5.2
Chronograf: 1.5.0.1
Telegraf (StatsD): 1.6.2-1
Grafana: 5.2.4
```

#### Start container with:
```
docker run --ulimit nofile=66000:66000 \
  -d \
  --name docker-statsd-influxdb-grafana \
  -p 3003:3003 \
  -p 3004:8888 \
  -p 8086:8086 \
  -p 22022:22 \
  -p 8125:8125/udp \
  -v influxdatabase:/var/lib/influxdb \
  docker-statsd-influxdb-grafana:latest
#  samuelebistoletti/docker-statsd-influxdb-grafana:latest
```
You can replace latest with the desired version listed in changelog file.

#### To stop the container:
```
docker stop docker-statsd-influxdb-grafana
```

#### To start the container again:
```
docker start docker-statsd-influxdb-grafana
```

#### login to the docker instance:
```
ssh root@localhost -p 22022
```
Password: ```root```

#### Make ssh tunnels for remote access:
```
ssh -N -f -L localhost:8086:localhost:8086 pi@dvt6.local -o ServerAliveInterval=30
ssh -N -f -L localhost:3003:localhost:3003 pi@dvt6.local -o ServerAliveInterval=30
ssh -N -f -L localhost:3004:localhost:3004 pi@dvt6.local -o ServerAliveInterval=30
```

#### Mapped Ports
```
Host        Container        Service

3003        3003            grafana
3004        8888            influxdb-admin (chronograf)
8086        8086            influxdb
8125        8125            statsd
22022        22        sshd
SSH
ssh root@localhost -p 22022
Password: root
```

#### Grafana
```
Open http://localhost:3003

Username: root
Password: root
```
Add data source on Grafana
Using the wizard click on Add data source
- Choose a name for the source and flag it as Default
- Choose InfluxDB as type
- Choose direct as access
- Fill remaining fields as follows and click on Add without altering other fields
```
Url: http://localhost:8086
Database:    telegraf
User: telegraf
Password:    telegraf
```
Basic auth and credentials must be left unflagged. Proxy is not required.

Now you are ready to add your first dashboard and launch some query on database.

#### InfluxDB
```
Web Interface
Open http://localhost:3004

Username: root
Password: root
Port: 8086
```

#### InfluxDB Shell (CLI)
- Establish a ssh connection with the container
- Launch ```influx``` to open InfluxDB Shell (CLI)


## Example Usage

```
from influxdb import InfluxDBClient
from datetime import datetime
from time import sleep

def body(c):
    return [
        {
            "measurement": "cpu_load_short",
            "tags": {
                "host": "server01",
                "region": "us-west"
            },
            "time": datetime.isoformat(datetime.utcnow()),
        "fields": {
            "Float_value": 0.64,
            "Int_value": c,
            "String_value": "Text",
            "Bool_value": True
        }
    }
]

count=100
host     = 'localhost'
port     = 8086
user     = 'root'
password = 'root'
dbname   = 'test'
dbuser   = 'grafana'
dbuser_password = 'grafana'
query = 'select Int_value, Float_value from cpu_load_short;'
client = InfluxDBClient(host, port, user, password, dbname)
print("Create database: " + dbname)
client.create_database(dbname)
#print("Create a retention policy")
#client.create_retention_policy('awesome_policy', '3d', 3, default=True)
print("Switch user: " + dbuser)
client.switch_user(dbuser, dbuser_password)
for i in range(count):
    json_body=body(i)
    print("Write points: {0}".format(json_body))
    client.write_points(json_body)
    sleep(1)
print("Querying data: " + query)
result = client.query(query)
print("Result: {0}".format(len(result)))
print("Switch user: " + user)
client.switch_user(user, password)
#print("Drop database: " + dbname)
#client.drop_database(dbname)
```

## Alternate Docker based installations
These alternatives were tried and found to have issues with network connectivity.
### from https://github.com/mlabouardy/telegraf-influxdb-grafana
Runs on Ubuntu 16.04

```
version: "2"
services:
  influxdb:
    container_name: influxdb
    image: influxdb:1.6.2
    ports:
      - "8083:8083"
      - "8086:8086"
    volumes:
      - /home/core/volumes/influxdb:/var/lib/influxdb
    restart: always

  grafana:
    container_name: grafana
    image: grafana/grafana:5.1.0
    ports:
      - "3000:3000"
    links:
      - influxdb
    restart: always

  telegraf:
    container_name: telegraf
    image: telegraf:1.7.4
    network_mode: "host"
    volumes:
      - /home/parallels/telegraf-influxdb-grafana/conf/telegraf/telegraf.conf
      - /var/run/docker.sock:/var/run/docker.sock
    restart: always
```

### From: `https://github.com/matisku/tig-stack/blob/master/docker-compose.yml`
Runs on Raspberry Pi

```
mkdir tig-stack
cd tig-stack
curl -OL https://raw.githubusercontent.com/matisku/tig-stack/master/docker-compose.yml
```
Edit the `docker-compose.yml` file to customize for our usage

```
grafana:
    image: matisq/grafana:latest
    ports:
        - 3000:3000
    links:
        - influxdb:influxdb
    environment:
        GF_SECURITY_ADMIN_USER: admin
        GF_SECURITY_ADMIN_PASSWORD: admin
        GF_SECURITY_SECRET_KEY: grafana
        GF_USERS_ALLOW_SIGN_UP: "true"
        GF_USERS_ALLOW_ORG_CREATE: "true"
        GF_AUTH_ANONYMOUS_ENABLED: "true"
        GF_AUTH_ANONYMOUS_ORG_NAME: grafana
        GF_DASHBOARDS_JSON_ENABLED: "true"
        GF_DASHBOARDS_JSON_PATH: /opt/grafana
    volumes_from:
        - grafana-data
    restart: always

grafana-data:
    image: busybox
    tty: true
    volumes:
        - /var/lib/grafana
        - /var/log/grafana
        - /var/lib/grafana/plugins

influxdb:
    image: matisq/influxdb:latest
    ports:
        - 8083:8083
        - 8086:8086
    environment:
        INFLUX_DATABASE: "telegraf"
        INLFUX_ADMIN_USER: "grafana"
        INFLUX_ADMIN_PASS: "grafana"
    volumes_from:
        - influxdb-data

influxdb-data:
    image: busybox
    tty: true
    volumes:
        - /var/lib/influxdb

telegraf:
    image: matisq/telegraf:latest
    links:
        - influxdb:influxdb
    environment:
        HOST_NAME: "telegraf"
        INFLUXDB_HOST: "influxdb"
        INFLUXDB_PORT: "8086"
        DATABASE: "telegraf"
    tty: true
    volumes:
        - /var/run/docker.sock:/var/run/docker.sock
    privileged: true
```

Now start up the trio.
```
docker-compose up -d
```
Access Grafana Dashboard from the browser
`http://localhost:3000`

## Alternate Install individual docker instances method
### Install InfluxDB
```
sudo docker run -d --volume=/var/influxdb:/data -p 8086:8086 hypriot/rpi-influxdb

sudo docker exec -it f7aeab6e116b /usr/bin/influx
> CREATE DATABASE db1
> SHOW DATABASES
> USE db1
> CREATE USER root WITH PASSWORD 'passhere' WITH ALL PRIVILEGES
> GRANT ALL PRIVILEGES ON db1 TO root
> SHOW USERS
```
Remember to change to container ID to the id of the influxdb container.
### Install Telegraf
```
sudo docker run --net=container:c10b584e3210 arm32v7/telegraf
sudo docker run --rm arm32v7/telegraf telegraf config > telegraf.conf

docker run --net=container:c10b584e3210 -v $PWD/telegraf.conf:/etc/telegraf/telegraf.conf:ro arm32v7/telegraf
```
### Install Grafana
```
docker run -i -p 3000:3000 --name grafana fg2it/grafana-armhf:v4.1.2
```


### Run TIG Suite
```
docker run -d -v /var/lib/grafana --name grafana-storage busybox:latest
docker run --rm -d --net=host --name grafana --volumes-from grafana-storage fg2it/grafana-armhf:v4.1.2
docker run --rm -d --name=influxdb --net=host --volume=/var/influxdb:/data hypriot/rpi-influxdb
docker run --rm -d --net=host --name telegraf -v $PWD/telegraf.conf:/etc/telegraf/telegraf.conf:ro arm32v7/telegraf
docker ps
docker logs influxdb
docker logs telegraf
docker logs grafana
```

## Alternate Example Usage
```
def main(host='localhost', port=8086):
    """Instantiate a connection to the InfluxDB."""
    user = 'grafana'
    password = 'grafana'
    dbname = 'telegraf'
    dbuser = 'grafana'
    dbuser_password = 'grafana'
    query = 'select value from cpu_load_short;'
    json_body = [
        {
            "measurement": "cpu_load_short",
            "tags": {
                "host": "server01",
                "region": "us-west"
            },
            "time": "2018-03-21T23:00:00Z",
            "fields": {
                "Float_value": 0.64,
                "Int_value": 3,
                "String_value": "Text",
                "Bool_value": True
            }
        }
    ]
    client = InfluxDBClient(host, port, user, password, dbname)
    print("Create database: " + dbname)
    client.create_database(dbname)
    print("Create a retention policy")
    #client.create_retention_policy('awesome_policy', '3d', 3, default=True)
    print("Switch user: " + dbuser)
    #client.switch_user(dbuser, dbuser_password)
    print("Write points: {0}".format(json_body))
    client.write_points(json_body)
    print("Querying data: " + query)
    result = client.query(query)
    print("Result: {0}".format(result))
    print("Switch user: " + user)
    client.switch_user(user, password)
    print("Drop database: " + dbname)
    client.drop_database(dbname)
```
