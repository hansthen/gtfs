This program provides a real time visual feed of metro lines
in Rotterdam.

Installation
===================
To install the simulator, you need to install docker first and then build
```shell
docker build -t ret .
docker run --net=host --env="DISPLAY" --volume="$HOME/.Xauthority:/root/.Xauthority:rw" -i -t ret
```

Extra packages during development
1. pip install psychopg2
2. apt install libpq-dev
3. docker run --name=postgis -d -e POSTGRES_USER=hans -e POSTGRES_PASS=password -e POSTGRES_DBNAME=gis -e ALLOW_IP_RANGE=0.0.0.0/0 -p 5432:5432 -v pg_data:/var/lib/postgresql --restart=always kartoza/postgis:9.6-2.4
4. apt install postgresql-client
5.

# how to query ov data
1. met welke lijn?
select trip_id from stop_times where trip_id in (select trip_id from trips where service_id in (select service_id from calendar_dates where date = '20200416')) and stop_id in (select stop_id from stops where similarity(stop_name, 'veldhoven, runstraat') > 0.7) and arrival_time > '09:00:00' and arrival_time < '09:30:00';

2. toon de dienstregeling voor die lijn
gis=# select stop_name, arrival_time, stop_sequence, stop_lat, stop_lon from stop_times, stops where stop_times.trip_id = '110771691' and stop_times.stop_id = stops.stop_id order by cast(stop_sequence as int);
              stop_name              | arrival_time | stop_sequence | stop_lat  | stop_lon
-------------------------------------+--------------+---------------+-----------+----------
 Bergeijk, Loo                       | 08:52:00     | 0             | 51.312932 | 5.344015
 Bergeijk, Broekstraat               | 08:53:00     | 1             | 51.312207 | 5.35252
 Bergeijk, Kennedylaan               | 08:53:00     | 2             | 51.314176 | 5.355445
 Bergeijk, Kervelstraat              | 08:54:00     | 3             | 51.316387 | 5.352216
 Bergeijk, Churchilllaan             | 08:54:00     | 4             | 51.31981  | 5.349474
 Bergeijk, Nieuwstraat               | 08:56:00     | 5             | 51.323569 | 5.351981
 Bergeijk, Van Beverwijkstraat       | 08:57:00     | 6             | 51.323642 | 5.357791
 Bergeijk, Hof                       | 08:57:00     | 7             | 51.323041 | 5.361048
 Bergeijk, Mr. Pankenstraat          | 08:58:00     | 8             | 51.322439 | 5.366385
 Bergeijk, Schutsboom                | 08:58:00     | 9             | 51.322062 | 5.369943
 Bergeijk, Eijkereind                | 08:59:00     | 10            | 51.323618 | 5.376154
 Westerhoven, Heijerstraat           | 09:00:00     | 11            | 51.327861 | 5.38743
 Westerhoven, Dorpstraat             | 09:01:00     | 12            | 51.329425 | 5.392595
 Westerhoven, Heuvel                 | 09:03:00     | 13            | 51.334333 | 5.399555
 Riethoven, Kerk                     | 09:07:00     | 14            | 51.352508 | 5.386052
 Riethoven, Walik                    | 09:09:00     | 15            | 51.363636 | 5.382247
 Keersop, Keersopperdreef            | 09:14:00     | 16            | 51.38029  | 5.413788
 Veldhoven, Volmolenweg              | 09:16:00     | 17            | 51.389181 | 5.407702
 Veldhoven, Locht                    | 09:18:00     | 18            | 51.400616 | 5.395191
 Veldhoven, Dorpstraat               | 09:19:00     | 19            | 51.403609 | 5.396686
 Veldhoven, Runstraat                | 09:21:00     | 20            | 51.405864 | 5.40633
 Veldhoven, ASML-gebouw 4            | 09:24:00     | 21            | 51.405925 | 5.414939
 Veldhoven, MMC Veldhoven Kempenbaan | 09:25:00     | 22            | 51.408046 | 5.417355
 Veldhoven, Veenstraat               | 09:27:00     | 23            | 51.412467 | 5.423064
 Veldhoven, Provincialeweg-Oost      | 09:28:00     | 24            | 51.416636 | 5.425942
 Eindhoven, Kastelenplein            | 09:31:00     | 25            | 51.418105 | 5.43927
 Eindhoven, Gagelbosch               | 09:32:00     | 26            | 51.419711 | 5.446445
 Eindhoven, Grieglaan                | 09:34:00     | 27            | 51.423833 | 5.453683
 Eindhoven, Donizettilaan            | 09:35:00     | 28            | 51.426868 | 5.458173
 Eindhoven, Solmsweg                 | 09:37:00     | 29            | 51.429751 | 5.462046
 Eindhoven, Mecklenburgstraat        | 09:39:00     | 30            | 51.433496 | 5.467474
 Eindhoven, Grote Berg               | 09:41:00     | 31            | 51.435666 | 5.47533
 Eindhoven, Vrijstraat               | 09:43:00     | 32            | 51.438407 | 5.475277
 Eindhoven, Piazza                   | 09:45:00     | 33            | 51.441796 | 5.475413
 Eindhoven, Station                  | 09:48:00     | 34            | 51.443663 | 5.478553

