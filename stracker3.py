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

from handlers import StudentHandler, EventHandler, FileHandler

UPLOAD_FOLDER = '/srv/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'doc', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp'])

### db
db = redis.StrictRedis(host='10.1.5.13', port=6379, db=0)

app = Flask(__name__)
app.secret_key = "W\xa8\x01\x83c\t\x06\x07p\x9c\xed\x13 \x98\x17\x0f\xf9\xbe\x18\x8a|I\xf4U"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

store = RedisStore(redis.StrictRedis(host='10.1.5.13', port=6379, db=1))

# this will replace the app's session handling
KVSessionExtension(store, app)



"""

REDIS DB SCHEMA

student:list     list   (of ids)
student:maxid
student:id    hash
	id type(afterschool/normal) firstname lastname grade selfsign(true/false)
student:id:events     list   (of event ids)
student:id:documents    list   (of document ids)
student:id:guardians    list   (of ids)
student:id:current_event    nameofevent
student:id:signed_into_afterschool true/false

deleted:student:list   list (of deleted ids)

guardian:list   list (of ids)
gaurdian:maxid
guardian:id hash
	id name phone relationship

event:list
event:maxid
event:id     hash
	id type title unix_time_stamp author ip_address sister_event (guardian)

event_title:list

document:list
document:maxid
document:id
	id filename filepath unix_time_stamp

"""


### std functions

def methodTimer(function):
	@wraps(function)
	def decorated_view(*args, **kwargs):
		t = time.time()
		result = function(*args, **kwargs)
		print function.__name__ + " took " + str(time.time() - t) + " seconds."
		return result
	return decorated_view

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




sh = StudentHandler(db)
eh = EventHandler(db)
fh = FileHandler(db, ALLOWED_EXTENSIONS)



#### ROUTING

@app.route("/", methods=['GET'])
@requireLogin
def route_default():

	students=[]
	event_titles = eh.get_all_titles()

	if 'grade' in request.args:
		students = sh.get_grade(request.args.get("grade"))
	elif 'term' in request.args:
		students = sh.get_all()
		matches = []
		for student in students:
			terms = request.args.get('term')
			terms = terms.split(" ")
			print terms

			for term in terms:
				if student['lastname'].lower() == term:
					matches.append(student)
				if student['firstname'].lower() == term:
					matches.append(student)

		students = matches
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
				print "grabbed username: " + rfuser
				if rfuser.lower() not in ['elemlab', 'group1', 'group2', 'group3', 'group4', 'group5']:
                                        print "user name is acceptable."
					session['user'] = request.form["username"]
					print "starting return for route_default"
					return redirect(url_for("route_default"))

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
				student_type = "normal"
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

				if 'afterschoolstudent' in request.form:
					student_type = "afterschool"

				sh.add(firstname=request.form["firstname"], 
					student_type=student_type, 
					lastname=request.form["lastname"], 
					grade=request.form["grade"], 
					guardians=guards, 
					selfsign=selfsign)

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

@app.route("/student/view/<student_id>/update", methods=['POST'])
@requireLogin
def route_student_view_update(student_id):

	if 'self_signout' in request.form:
		db.hset("student:"+student_id, "selfsign", "True")
		flash("Updated to allow self signing.")
	else:
		db.hset("student:"+student_id, "selfsign", "False")
		flash("Updated to disallow self signing.")

	if 'afterschoolstudent' in request.form:
		db.hset("student:"+student_id, "type", "afterschool")
		flash("Added student to afterschool program.")
	else:
		flash("Removed student from afterschool program.")
		db.hset("student:"+student_id, "type", "normal")

	return redirect(url_for("route_student_view", student_id=student_id))

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



@app.route("/event/manage", methods=['GET', 'POST'])
@requireLogin
def route_event_manage():

	if request.method == "POST":
		if 'event_type' in request.form:
			eh.create_title(title=request.form['event_type'])
			flash("Event '%s' was created." % (request.form['event_type']))

	titles = eh.get_all_titles()		
	print titles
	return render_template("manage_events.html", titles=titles)

@app.route("/event/delete/<title>", methods=['GET', 'POST'])
@requireLogin
def route_event_delete(title):

	eh.remove_title(title)

	return redirect(url_for("route_event_manage"))

@app.route("/event/signin", methods=['GET', 'POST'])
@requireLogin
def route_event_signin():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form:
			sid = request.form['student_id']
			if request.form['title'] == 'Afterschool':
				eid = eh.create_event(student_id=request.form['student_id'], event_type="ASstart", title="Afterschool", author=session['user'], ip_address=request.remote_addr)
				db.set("student:"+sid+":signed_into_afterschool", "True")
			else:
				### check if student is part of afterschool prgm
				### if they are auto sign into the afterschool first
				if db.hget("student:"+sid, "type") == "afterschool" and db.get("student:"+sid+":signed_into_afterschool") == "False":
					eid = eh.create_event(student_id=request.form['student_id'], event_type="ASstart", title="Afterschool", author=session['user'], ip_address=request.remote_addr)
					db.set("student:"+sid+":signed_into_afterschool", "True")
				eid = eh.create_event(student_id=request.form['student_id'], event_type="start", title=request.form['title'], author=session['user'], ip_address=request.remote_addr)
			
			return request.form['student_id']
	return "Error"

@app.route("/event/update", methods=['GET'])
@requireLogin
def route_event_update():

	if 'student_id' in request.args:
		sid = request.args.get("student_id")
		events = eh.get_todays_events(student_id=sid)
		events = sorted(events, key=lambda k: k['unix_time_stamp'])
		return str(json.dumps(events))

	return "Error"

@app.route("/event/update/all", methods=['GET'])
#@methodTimer
@requireLogin
def route_event_update_all():

	students = sh.get_all_student_ids()

	return_list = []

	for student_id in students:
		events = eh.get_todays_events(student_id)
#		events = sorted(events, key=lambda k: k['unix_time_stamp'])
		return_list.append(events)

	return str(json.dumps(return_list))

@app.route("/event/bathroom", methods=['GET', 'POST'])
@requireLogin
def route_event_bathroom():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form:
			eid = eh.create_event(student_id=request.form['student_id'], event_type="start", title="Restroom", author=session['user'], ip_address=request.remote_addr)
			return request.form['student_id']

	return "Error"

@app.route("/event/absent", methods=['GET', 'POST'])
@requireLogin
def route_event_absent():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form:
			eid = eh.create_event(student_id=request.form['student_id'], event_type='start', title="Absent", author=session['user'], ip_address=request.remote_addr)

	return "Error."

@app.route("/event/signout", methods=['GET', 'POST'])
@requireLogin
def route_event_signout():

	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form:
			if sh.current_event(request.form['student_id']) != "NO_CURRENT_EVENT":
				current_event = sh.current_event(request.form['student_id'])
				eid = eh.create_event(
								student_id=request.form['student_id'], 
								event_type="end", title=current_event, 
								author=session['user'], 
								ip_address=request.remote_addr)
				return request.form['student_id']
			else:
				return "Error. Student not signed into anything."
	return "Error."

@app.route("/event/afterschoolsignout", methods=['GET', 'POST'])
@requireLogin
def route_event_afterschoolsignout():
	if request.method == "POST":
		if 'student_id' in request.form and 'title' in request.form and 'guardian' in request.form:
			db.set("student:"+request.form['student_id']+":signed_into_afterschool", "False")
			db.set("student:"+request.form['student_id']+":current_event", "NO_CURRENT_EVENT")
			eid = eh.create_event(
					student_id=request.form['student_id'], 
					event_type="ASend", 
					title="Afterschool", 
					author=session['user'], 
					guardian=request.form['guardian'], 
					ip_address=request.remote_addr)

			return request.form['student_id']
	return "Error."

@app.route("/status", methods=['GET'])
@requireLogin
def route_status():

	dct = {}
	dct['count_general'] = sh.count_general()
	dct['count_afterschool'] = sh.count_afterschool()

	return json.dumps(dct)

@app.route("/status/view", methods=['GET'])
@requireLogin
def route_status_view():
	## get students in afterschool
	afterschool_ids = sh.ids_afterschool()
	general_ids = sh.ids_general()
	afterschool_students = []
	general_students = []

	for id in afterschool_ids:
		afterschool_students.append( sh.get_one(id) )

	for id in general_ids:
		general_students.append( sh.get_one(id) )

	return render_template("students.html", 
			afterschoolers=sorted(afterschool_students, key=lambda k:k['lastname']), 
			students=sorted(general_students, key=lambda k:k['lastname']))

if __name__ == "__main__":
	#presets()

	app.debug = True
	app.run(host='0.0.0.0')







