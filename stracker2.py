### flask stuff
from flask import Flask, render_template, session, redirect, url_for, abort, request, flash, send_from_directory

### session managment stuff
from flaskext.kvsession import KVSessionExtension
import redis
from simplekv.memory.redisstore import RedisStore

### for login wrapper
from functools import wraps

### ldap
import ldap

### misc
import time
import json
import datetime

### uploads
import os
from werkzeug import secure_filename

UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'doc', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp'])

### db
db = redis.StrictRedis(host='10.1.5.12', port=6379, db=0)

app = Flask(__name__)
app.secret_key = "W\xa8\x01\x83c\t\x06\x07p\x9c\xed\x13 \x98\x17\x0f\xf9\xbe\x18\x8a|I\xf4U"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# The process running Flask needs write access to this directory:
store = RedisStore(redis.StrictRedis(host='10.1.5.12', port=6379, db=1))

# this will replace the app's session handling
KVSessionExtension(store, app)



"""

REDIS DB SCHEMA

student:list     list   (of ids)
student:maxid
student:id    hash
	id firstname lastname grade selfsign(true/false)
student:id:events     list   (of event ids)
student:id:documents    list   (of document ids)
student:id:guardians    list   (of ids)

deleted:student:list   list (of deleted ids)

guardian:list   list (of ids)
gaurdian:maxid
guardian:id hash
	id name phone relationship

event:list
event:maxid
event:id     hash
	id title unix_time_stamp_start unix_time_stamp_end start_teacher end_teacher ip_address (guardian)

event_title:list

document:list
document:maxid
document:id
	id filename filepath unix_time_stamp

"""

class FileHandler():

	def __init__(self, db):
		self.db = db

	def allowed_file(self, filename):
	    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

	def save_file_to_db(self, filename, filepath, student_id):
		fid = str( self.db.incr("document:maxid") )
		self.db.rpush("document:list", fid)
		self.db.rpush("student:"+student_id+":documents", fid)
		self.db.hmset("document:"+fid, { "id":fid, "filename":filename, "filepath": filepath, "unix_time_stamp": time.time() })


class StudentHandler():

	def __init__(self, db):
		self.db = db

	def add(self, firstname, lastname, grade, selfsign=False, guardians=[]):
		firstname = firstname.strip(" ")
		lastname = lastname.strip(" ")
		grade = grade.strip(" ")

		sid = str(self.db.incr("student:maxid"))
		self.db.rpush("student:list", sid)
		self.db.hmset("student:"+sid, { "id":sid, "firstname":firstname, "lastname":lastname, "grade":grade, "selfsign":selfsign })

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

		return student

	def get_events(self, student_id):
		eids = self.db.lrange("student:"+student_id+":events", 0, -1)
		events = []
		for eid in eids:
			event = self.db.hgetall("event:"+eid)
			start_time = ""
			end_time = ""
			if event['unix_time_stamp_start'] != "":
				start_time = time.ctime(float(event['unix_time_stamp_start']))
			if event['unix_time_stamp_end'] != "":
				end_time = time.ctime(float(event['unix_time_stamp_end']))
			event['nice_time_start'] = start_time
			event['nice_time_end'] = end_time
			events.append(event)

		return events

	def get_todays_events(self, student_id):
		eids = self.db.lrange("student:"+student_id+":events", 0, -1)
		events = []
		for eid in eids:
			event = self.db.hgetall("event:"+eid)
			date = datetime.datetime.fromtimestamp(float(event["unix_time_stamp_start"]))
			today = datetime.datetime.fromtimestamp(time.time())
			if date.year == today.year and date.month == today.month and date.day == today.day:
				events.append(event)

		return events

	def get_files(self, student_id):
		fids = self.db.lrange("student:"+student_id+":documents", 0, -1)
		docs = []
		for fid in fids:
			docs.append(self.db.hgetall("document:"+fid))

		return docs


class EventHandler():
	
	def __init__(self, db):
		self.db = db

	def create_title(self, title):
		self.db.rpush("event_title:list", title)
		return True

	def get_all_titles(self):
		titles = self.db.lrange("event_title:list", 0, -1)
		return titles

	def end_event(self, student_id, time_stamp, teacher):
		### get students last event
		last_eid = self.db.lindex("student:"+student_id+":events", -1)
		if last_eid != None:
			print "updating timestamp of last event."
			print last_eid
			### check that it's not set already
			if self.db.hget("event:"+last_eid, "unix_time_stamp_end") == "":
				self.db.hset("event:"+last_eid, "unix_time_stamp_end", time_stamp)
				self.db.hset("event:"+last_eid, "end_teacher", teacher)

	def create_event(self, student_id, title, ending_event, teacher, ip_address="", guardian=""):
		time_stamp = time.time()

		### end their last event
		self.end_event(student_id=student_id, time_stamp=time_stamp, teacher=teacher)

		eid = str(self.db.incr("event:maxid"))

		self.db.rpush("event:list", eid)

		end_teacher = ""
		end_time_stamp = ""
		if ending_event == True:
			end_teacher = teacher
			end_time_stamp = time_stamp

		self.db.hmset("event:"+eid, { 
										"id":eid, 
										"title":title, 
										"start_teacher":teacher,
										"end_teacher": end_teacher,
										"ip_address":ip_address, 
										"unix_time_stamp_start":time_stamp,
										"unix_time_stamp_end":end_time_stamp,
										"guardian":guardian
									})

		self.db.rpush("student:"+student_id+":events", eid)

		return eid


sh = StudentHandler(db)
eh = EventHandler(db)
fh = FileHandler(db)

### std functions

def requireLogin(fn):
	@wraps(fn)
	def decorated(*args, **kwargs):
		if 'user' in session:
			return fn(*args, **kwargs)
		return redirect(url_for("route_login"))
	return decorated

def check_ldap_credentials(username, password, server_ip):
	ldap_server="ldap://" + server_ip
	con = ldap.initialize(ldap_server)
	user = username + "@southside.edu"
	try:
		con.simple_bind_s(user,password)
		con.unbind_s()
		print "authentication successful"
		return True
	except ldap.LDAPError:
		con.unbind_s()
		print "authentication error"
		return False

#### ROUTING

@app.route("/", methods=['GET'])
@requireLogin
def route_default():

	students=[]
	event_titles = eh.get_all_titles()

	if 'grade' in request.args:
		students = sh.get_grade(request.args.get("grade"))
	else:
		students = sh.get_all()

	students = sorted(students, key= lambda k:k['lastname'])

	return render_template("mainpage.html", students=students, event_titles=event_titles)

@app.route("/login", methods=['GET', 'POST'])
def route_login():
	if request.method == "POST":
		if "username" in request.form and "password" in request.form:
			if check_ldap_credentials(request.form["username"], request.form["password"], "10.1.5.9"):
				rfuser = request.form['username']
				if rfuser.lower() not in ['elemlab', 'group1', 'group2', 'group3', 'group4', 'group5']:
					session['user'] = request.form["username"]
					return redirect(url_for("route_default"))
					return redirect(url_for("route_login"))

	return render_template("login.html")

@app.route("/logout")
@requireLogin
def route_logout():
	if "user" in session:
		session.pop("user", None)

	return redirect(url_for("route_login"))

@app.route("/student/create", methods=['GET', 'POST'])
@requireLogin
def route_student_create():

	if request.method == "POST":
		if 'firstname' in request.form and 'lastname' in request.form and 'grade' in request.form:
			if request.form['firstname'] != "" and request.form["lastname"] != "" and request.form["grade"] != "":
				guards = []
				selfsign = "False"
				if request.form['guardian1'] != "":
					gid = sh.create_guardian(name=request.form['guardian1'], phone=request.form['guardian1phone'], relationship=request.form['guardian1relationship'])
					guards.append(gid)
				if request.form['guardian2'] != "":
					gid = sh.create_guardian(name=request.form['guardian2'], phone=request.form['guardian2phone'], relationship=request.form['guardian2relationship'])
					guards.append(gid)
				if request.form['guardian3'] != "":
					gid = sh.create_guardian(name=request.form['guardian3'], phone=request.form['guardian3phone'], relationship=request.form['guardian3relationship'])
					guards.append(gid)
				if request.form['guardian4'] != "":
					gid = sh.create_guardian(name=request.form['guardian4'], phone=request.form['guardian4phone'], relationship=request.form['guardian4relationship'])
					guards.append(gid)

				if 'self_signout' in request.form:
					selfsign = "True"

				sh.add(firstname=request.form["firstname"], lastname=request.form["lastname"], grade=request.form["grade"], guardians=guards, selfsign=selfsign)
				flash("%s, %s was added successfully." % (request.form['lastname'], request.form['firstname']))
			else:
				flash("Error. Firstname, Lastname, Grade are Required.")
	return render_template("addstudent.html")

@app.route("/student/view/<student_id>", methods=['GET'])
@requireLogin
def route_student_view(student_id):
	student = sh.get_one(student_id)
	events = sh.get_events(student_id)
	documents = sh.get_files(student_id)

	return render_template("viewstudent.html", student=student, events=events, documents=documents)

@app.route("/student/view/<student_id>/documents/add", methods=['GET','POST'])
@requireLogin
def route_student_view_documents_add(student_id):

	if request.method == "POST":
		file = request.files['file']
		if file and fh.allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			fh.save_file_to_db(filename=filename, filepath=app.config['UPLOAD_FOLDER'], student_id=student_id)
			flash(""" %s uploaded successfully.""" % (file.filename))
			return redirect(url_for("route_student_view", student_id=student_id))

		else:
			flash("Error uploading file.")

	return render_template("add_document.html")

@app.route('/student/view/<student_id>/documents/<filename>')
@requireLogin
def route_uploaded_file(student_id, filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route("/student/delete/<student_id>")
@requireLogin
def route_student_delete(student_id):

	sh.delete(student_id)

	return redirect(url_for("route_default"))

@app.route("/student/<student_id>/guardian/create", methods=['GET', "POST"])
@requireLogin
def route_student_guardian_create(student_id):

	if request.method == "POST":
		sid = student_id
		gid = sh.create_guardian(name=request.form['guardian'], phone=request.form['guardianphone'], relationship=request.form['guardianrelationship'])
		db.rpush("student:"+sid+":guardians", gid)
		flash("Guardian '%s' was added." % (request.form['guardian']))
		return redirect(url_for("route_student_view", student_id=student_id))

	return render_template("addguardian.html", student_id=student_id)



@app.route("/event/create", methods=['GET', 'POST'])
@requireLogin
def route_event_create():

	if request.method == "POST":
		if 'event_type' in request.form:
			eh.create_title(title=request.form['event_type'])
			flash("Event '%s' was created." % (request.form['event_type']))

	return render_template("addevent.html")

@app.route("/event/signin", methods=['GET', 'POST'])
@requireLogin
def route_event_signin():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form:
			eid = eh.create_event(student_id=request.form['student_id'], title=request.form['title'], teacher=session['user'], ending_event=False)
			return request.form['student_id']
	return "Error"

@app.route("/event/update", methods=['GET'])
@requireLogin
def route_event_update():

	if 'student_id' in request.args:
		sid = request.args.get("student_id")
		events = sh.get_todays_events(student_id=sid)
		events = sorted(events, key=lambda k: k['unix_time_stamp_start'], reverse=True)
		return str(json.dumps(events))

	return "Error"

@app.route("/event/bathroom", methods=['GET', 'POST'])
@requireLogin
def route_event_bathroom():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form:
			eid = eh.create_event(student_id=request.form['student_id'], title=request.form['title'], teacher=session['user'], ending_event=False)
			return request.form['student_id']

	return "Error"

@app.route("/event/absent", methods=['GET', 'POST'])
@requireLogin
def route_event_absent():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form:
			eid = eh.create_event(student_id=request.form['student_id'], title=request.form['title'], teacher=session['user'], ending_event=True)
			return request.form['student_id']

	return "Error."

@app.route("/event/signout", methods=['GET', 'POST'])
@requireLogin
def route_event_signout():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form and 'guardian' in request.form:
			if request.form['guardian'] == "":
				return "Error."
			eid = eh.create_event(student_id=request.form['student_id'], title=request.form['title'], teacher=session['user'], guardian=request.form['guardian'], ending_event=True)
			return request.form['student_id']
	return "Error."




if __name__ == "__main__":
	#presets()

	app.debug = True
	app.run(host='0.0.0.0')
