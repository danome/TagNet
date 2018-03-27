docker run -d -v /var/lib/grafana --name grafana-storage busybox:latest
docker run --rm -d --net=host --name grafana --volumes-from grafana-storage fg2it/grafana-armhf:v4.1.2
docker run --rm -d --name=influxdb --net=host --volume=/var/influxdb:/data hypriot/rpi-influxdb
docker run --rm -d --net=host --name telegraf -v $PWD/telegraf.conf:/etc/telegraf/telegraf.conf:ro arm32v7/telegraf
docker ps
docker logs influxdb
docker logs telegraf
docker logs grafana
