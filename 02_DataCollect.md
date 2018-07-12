## Install Docker
```
curl -fsSL get.docker.com -o get-docker.sh
sudo sh get-docker.sh

sudo usermod -aG docker `whoami`
```
Remember to restart your terminal session to activate the new group.

## Install TIG Suite (Telegraf-InfluxDB-Grafana)
From: `https://github.com/matisku/tig-stack/blob/master/docker-compose.yml`
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

## Alternate Install method
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

## Example Usage
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

```
def body(c):
    return [
        {
            "measurement": "cpu_load_short",
            "tags": {
                "host": "server01",
                "region": "us-west"
            },
        "time": "2018-03-21T23:00:01Z",
        "fields": {
            "Float_value": 0.64,
            "Int_value": c,
            "String_value": "Text",
            "Bool_value": True
        }
    }
]

count=1
user = 'grafana'
password = 'grafana'
dbname = 'telegraf'
dbuser = 'grafana'
dbuser_password = 'grafana'
query = 'select Int_value, Float_value from cpu_load_short;'
client = InfluxDBClient(host, port, user, password, dbname)
print("Create database: " + dbname)
client.create_database(dbname)
print("Create a retention policy")
client.create_retention_policy('awesome_policy', '3d', 3, default=True)
print("Switch user: " + dbuser)
client.switch_user(dbuser, dbuser_password)
print("Write points: {0}".format(json_body))
client.write_points(json_body)
print("Querying data: " + query)
result = client.query(query)
print("Result: {0}".format(result))
print("Switch user: " + user)
client.switch_user(user, password)
#print("Drop database: " + dbname)
#client.drop_database(dbname)
```
