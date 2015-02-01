# tardis

WORK IS IN PROGRESS!!!

`tardis` is a tool to handle the state of your test DB in an efficent way. You can create checkpoints for your DB state to `travel` to them back and forth.

`tardis` is based on 
- `Docker` to launch DB containers. See [Docker repository](https://registry.hub.docker.com/_/postgres/) for currently supported images
- `GIT` to create the checkpoints and to `travel` from one to another

# Setup

```shell
$ sudo pip3 install -r requirements.txt
$ python3 -m tardis
```

# First Steps

https://registry.hub.docker.com/_/postgres/

```shell
$ sudo -s
$ python3 -m tardis configure
$ travel plan name: first_try
> docker image [postgres]:
> docker image tag [latest]: 8.4
> DB user [postgres]:
> DB password [postgres]:
> DB port [5432]:
> data share between host and Docker container: /tmp/postgres

# launches the configured postgres docker image with configured credentials
$ python3 -m tardis run --travel-plan=first_try

# create checkpoint of current DB state
$ python3 -m tardis save --travel-plan=first_try --checkpoint=init
$ psql --username=postgres --host=localhost --port=5432  -c "create table test(id serial, description text)"
CREATE TABLE
                                              ^
$ psql --username=postgres --host=localhost --port=5432  -c "insert into test(description) values ('test1')"
INSERT 0 1
$ psql --username=postgres --host=localhost --port=5432  -c "insert into test(description) values ('test2')"
INSERT 0 1
$ psql --username=postgres --host=localhost --port=5432  -c "select * from test"
 id | description
----+-------------
  1 | test1
  2 | test2
(2 rows)

# create checkpoint of current DB state
$ python3 -m tardis save --travel-plan=first_try --checkpoint=initial_test_data

# which checkpoints do I have for my travel plan
$ python3 -m tardis list --travel-plan=first_try
> init
> initial_test_data

$ psql --username=postgres --host=localhost --port=5432  -c "insert into test(description) values ('test3')"
INSERT 0 1
$ psql --username=postgres --host=localhost --port=5432  -c "insert into test(description) values ('test4')"
INSERT 0 1
$ psql --username=postgres --host=localhost --port=5432  -c "select * from test"
 id | description
----+-------------
  1 | test1
  2 | test2
  3 | test3
  4 | test4
(4 rows)

# ooops...we do need these new statements. so let's travel back in time
$ python3 -m tardis travel-back --travel-plan=first_try
$ psql --username=postgres --host=localhost --port=5432  -c "select * from test"
 id | description
----+-------------
  1 | test1
  2 | test2
(2 rows)

# actually, I do not need any data...let's go back to the inital state
$ python3 -m tardis travel-to --travel-plan=first_try --checkpoint=init
$ psql --username=postgres --host=localhost --port=5432  -c "select * from test"
> ERROR:  relation "test" does not exist
> LINE 1: select * from test

# if I think about it, I do need some test data
$ python3 -m tardis travel-to --travel-plan=first_try --checkpoint=initial_test_data
$ psql --username=postgres --host=localhost --port=5432  -c "select * from test"
 id | description
----+-------------
  1 | test1
  2 | test2
(2 rows)

# stop image of travel plan 'first try'
$ python3 -m tardis stop --travel-plan=first_try
```




