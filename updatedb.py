import redis
import time

db = redis.StrictRedis(host='10.1.5.12', port=6379, db=0)


## select all students in db

ids = db.lrange("student:list", 0, -1)

## add fields current_event and signed_into_afterschool
## add fields student:id    type 
for id in ids:
	db.set("student:"+id+":current_event", "NO_CURRENT_EVENT")
	db.set("student:"+id+":signed_into_afterschool", "False")
	db.hset("student:"+id, "type", "afterschool")


ids = db.lrange("event:list", 0, -1)

### add fields type, unix_time_stamp, author, sister_event to event:id hash

for id in ids:
	db.hset("event:"+id, "type", "end")
	db.hset("event:"+id, "unix_time_stamp", str(time.time()))
	db.hset("event:"+id, "author", "csteinke")
	db.hset("event:"+id, "sister_event", "")

