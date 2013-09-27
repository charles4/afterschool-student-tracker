import time
import json
import datetime 

class FileHandler():

	def __init__(self, db, allowed_extensions):
		self.db = db
		self.allowed_extensions = allowed_extensions

	def allowed_file(self, filename):
	    return '.' in filename and filename.rsplit('.', 1)[1] in self.allowed_extensions

	def save_file_to_db(self, filename, filepath, student_id):
		fid = str( self.db.incr("document:maxid") )
		self.db.rpush("document:list", fid)
		self.db.rpush("student:"+student_id+":documents", fid)
		self.db.hmset("document:"+fid, { "id":fid, "filename":filename, "filepath": filepath, "unix_time_stamp": time.time() })


class StudentHandler():

	def __init__(self, db):
		self.db = db

	def add(self, student_type, firstname, lastname, grade, selfsign=False, guardians=[]):
		firstname = firstname.strip(" ")
		lastname = lastname.strip(" ")
		grade = grade.strip(" ")

		sid = str(self.db.incr("student:maxid"))
		self.db.rpush("student:list", sid)
		self.db.hmset("student:"+sid, { "id":sid, "type":student_type,"firstname":firstname, "lastname":lastname, "grade":grade, "selfsign":selfsign })
		self.db.set("student:"+sid+":signed_into_afterschool", "False")
		self.db.set("student:"+sid+":current_event", "NO_CURRENT_EVENT")
		for guardian in guardians:
			self.db.rpush("student:"+sid+":guardians", guardian)

		return sid

	def delete(self, student_id):
		sid=student_id
		self.db.rename("student:"+sid, "deleted:student:"+sid)
		try:
			self.db.rename("student:"+sid+":documents", "deleted:student:"+sid+":documents")
		except ResponseError:
			print "error renaming students:"+sid+":documents    key not found."
			
		self.db.rename("student:"+sid+":guardians", "deleted:student:"+sid+":guardians")
		self.db.rename("student:"+sid+":events", "deleted:student:"+sid+":events")
		self.db.rename("student:"+sid+":selfsign", "deleted:student:"+sid+":selfsign")
		self.db.lrem("student:list", 0, sid)
		self.db.rpush("deleted:student:list", sid)

		return sid

	def exists(self, student_id):
		student = self.db.hgetall("student:"+student_id)
		if student:
			return True
		else: 
			return False

	def create_guardian(self, name, phone, relationship):
		name = name.strip(" ")
		phone = phone.strip(" ")
		relationship = relationship.strip(" ")

		gid = str(self.db.incr("guardian:maxid"))
		self.db.rpush("guardian:list", gid)
		self.db.hmset("guardian:"+gid, { "id":gid, "name":name, "phone":phone, "relationship":relationship })

		return gid

	def get_all(self):
		sids = self.db.lrange("student:list", 0, -1)
		students = []
		for sid in sids:
			student = self.db.hgetall("student:"+str(sid))
			gids = self.db.lrange("student:"+sid+":guardians", 0, -1)
			guardians = []
			for gid in gids:
				guardians.append( self.db.hgetall("guardian:"+str(gid)) )

			student['current_event'] = self.db.get("student:"+sid+":current_event")
			student['signed_into_afterschool'] = self.db.get('student:'+sid+':signed_into_afterschool')

			student["guardians"] = guardians
			students.append( student )


		return students

	def get_grade(self, grade):
		sids = self.db.lrange("student:list", 0, -1)
		students = []
		for sid in sids:
			student = self.db.hgetall("student:"+str(sid))
			if student['grade'] == grade:
				gids = self.db.lrange("student:"+sid+":guardians", 0, -1)
				guardians = []
				for gid in gids:
					guardians.append( self.db.hgetall("guardian:"+str(gid)) )

				student["guardians"] = guardians
				students.append( student )


		return students

	def get_one(self, student_id):
		sid = student_id
		student = self.db.hgetall("student:"+str(sid))
		
		gids = self.db.lrange("student:"+sid+":guardians", 0, -1)
		guardians = []
		for gid in gids:
			guardians.append( self.db.hgetall("guardian:"+str(gid)) )

		student["guardians"] = guardians

		student['current_event'] = self.db.get("student:"+sid+":current_event")

		return student

	def get_events(self, student_id):
		eids = self.db.lrange("student:"+student_id+":events", 0, -1)
		events = []
		for eid in eids:
			event = self.db.hgetall("event:"+eid)
			start_time = ""
			if 'unix_time_stamp' in event:
				if event['unix_time_stamp'] != "":
					start_time = time.ctime(float(event['unix_time_stamp']))
					event['nice_time'] = start_time
					events.append(event)

		return events

	def get_files(self, student_id):
		fids = self.db.lrange("student:"+student_id+":documents", 0, -1)
		docs = []
		for fid in fids:
			docs.append(self.db.hgetall("document:"+fid))

		return docs

	def current_event(self, student_id):
		return self.db.get("student:"+student_id+":current_event")

	def count_general(self):

		ids = self.db.lrange("student:list", 0, -1)
		signed_in_students = []
		for id in ids:
			event = self.current_event(id)
			if event != "NO_CURRENT_EVENT":
				signed_in_students.append(id)

		return len(signed_in_students)


	def count_afterschool(self):

		ids = self.db.lrange("student:list", 0, -1)
		signed_in_students = []
		for id in ids:
			status = self.db.get("student:"+id+":signed_into_afterschool")
			if status == "True":
				signed_in_students.append(id)

		return len(signed_in_students)

	def ids_general(self):
		ids = self.db.lrange("student:list", 0, -1)
		signed_in_students = []
		for id in ids:
			event = self.current_event(id)
			if event != "NO_CURRENT_EVENT":
				signed_in_students.append(id)

		return signed_in_students

	def ids_afterschool(self):

		ids = self.db.lrange("student:list", 0, -1)
		signed_in_students = []
		for id in ids:
			status = self.db.get("student:"+id+":signed_into_afterschool")
			if status == "True":
				signed_in_students.append(id)

		return signed_in_students

	def get_all_student_ids(self):
		return self.db.lrange("student:list", 0, -1)

class EventHandler():
	
	def __init__(self, db):
		self.db = db

	def create_title(self, title):
		self.db.rpush("event_title:list", title)
		return True

	def get_all_titles(self):
		titles = self.db.lrange("event_title:list", 0, -1)
		return titles

	def remove_title(self, title):
		return self.db.lrem("event_title:list", 0, title)

	#@methodTimer
	def get_todays_events(self, student_id):
		eids = self.db.lrange("student:"+student_id+":events", 0, -1)
		events = []

		pipe = self.db.pipeline()
		for eid in eids:
			pipe.hgetall("event:"+eid)
		raw_events = pipe.execute()

		for event in raw_events:
			if "unix_time_stamp" in event:
				date = datetime.datetime.fromtimestamp(float(event["unix_time_stamp"]))
				today = datetime.datetime.fromtimestamp(time.time())
				if date.year == today.year and date.month == today.month and date.day == today.day:
					event['student_id'] = student_id
					events.append(event)

		return events

	def get_all_todays_events(self):
		eids = self.db.lrange("event:list", 0, -1)
		events = []
		for eid in eids:
			event = self.db.hgetall("event:"+eid)
			if "unix_time_stamp" in event:
				date = datetime.datetime.fromtimestamp(float(event["unix_time_stamp"]))
				today = datetime.datetime.fromtimestamp(time.time())
				if date.year == today.year and date.month == today.month and date.day == today.day:
					events.append(event)

		return events

	def create_event(self, student_id, event_type, title, author, ip_address="", guardian=""):
		time_stamp = time.time()

		eid = str(self.db.incr("event:maxid"))

		self.db.rpush("event:list", eid)

		if event_type == "end":
			sister_event = self.db.lrange("student:"+student_id+":events", -1, -2)
			### if student in afterschool, reset current event to afterschool
			if self.db.get('student:'+student_id+':signed_into_afterschool') == "True":
				self.db.set('student:'+student_id+':current_event', 'Afterschool')
			else:
				self.db.set("student:"+student_id+":current_event", "NO_CURRENT_EVENT")
		elif event_type == "ASend":
			events = self.get_todays_events(student_id)
			sister_event = ""
			for event in events:
				if event['type'] == "ASstart":
					sister_event = event['id']

		else:
			sister_event = ""
			self.db.set("student:"+student_id+":current_event", title)

		self.db.hmset("event:"+eid, { 
										"id":eid,
										"type":event_type,
										"title":title, 
										"author":author,
										"ip_address":ip_address, 
										"unix_time_stamp": time_stamp,
										"guardian":guardian,
										"sister_event": sister_event
									})

		self.db.rpush("student:"+student_id+":events", eid)

		return eid
