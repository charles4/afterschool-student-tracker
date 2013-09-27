import redis
from handlers import StudentHandler, EventHandler

db = redis.StrictRedis(host='10.1.5.13', port=6379, db=3)

sh = StudentHandler(db)
eh = EventHandler(db)

students = sh.get_all()

for student in students:
	id = student['id']
	if student['current_event'] != "NO_CURRENT_EVENT":
		current_event = sh.current_event(id)
		eid = eh.create_event(
								student_id=id, 
								event_type="end", title=current_event, 
								author="Administrator", 
								ip_address=""
								)

	if student['signed_into_afterschool'] == "True":
		db.set("student:"+id+":signed_into_afterschool", "False")
		db.set("student:"+id+":current_event", "NO_CURRENT_EVENT")
		eid = eh.create_event(
				student_id=id, 
				event_type="ASend", 
				title="Afterschool", 
				author="Administrator", 
				guardian="Adminstrative Signout (midnight reset)", 
				ip_address=""
				)