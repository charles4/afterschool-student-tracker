### flask stuff
from flask import Flask, render_template, session, redirect, url_for, abort, request, flash, send_from_directory

### session managment stuff
from flaskext.kvsession import KVSessionExtension
import redis
from simplekv.memory.redisstore import RedisStore

### for login wrapper
from functools import wraps


### mysql and ldap
import _mysql
import ldap

db = _mysql.connect("localhost", "charles", "6andromeda9", "stracker")


# The process running Flask needs write access to this directory:
store = RedisStore(redis.StrictRedis())

app = Flask(__name__)

# this will replace the app's session handling
KVSessionExtension(store, app)


app = Flask(__name__)
app.secret_key = "W\xa8\x01\x83c\t\x06\x07p\x9c\xed\x13 \x98\x17\x0f\xf9\xbe\x18\x8a|I\xf4U"

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


### db utility functions

def get_event_type_id(event_type):
	db.query("""SELECT * FROM event_types WHERE name="%s" """ % (event_type))
	r = db.store_result()
	r = r.fetch_row(maxrows=0, how=0)
	print r
	if r:
		return int(r[0][0])
	else:
		return None

def get_current_event_id(student_id):
	### check whether student is in a event already
	db.query(""" SELECT last_event FROM students WHERE id=%d """ % (student_id))
	r = db.store_result()
	r = r.fetch_row(maxrows=1, how=1)

	print "GET_CURRENT_EVENT_ID:"
	print r
	
	if r[0]["last_event"] != None:
		return int(r[0]["last_event"])
	else:
		return None

def get_event_direction(event_id):
	db.query(""" SELECT direction FROM events WHERE id=%d  """ % (int(event_id)))
	r = db.store_result()
	r = r.fetch_row(maxrows=1, how=1)

	print "GET EVENT DIRECTION -> "
	print r

	return r[0]["direction"]

def student_signin(EVENT_NAME, STUDENT_ID, etid):
	last_eid = None
	try:
		direction = "IN"
		### create vent
		db.query(""" INSERT INTO events (name, student_id, event_type_id, direction, author) VALUES ("%s", %d, %d, "%s", "%s") """ % 
			(EVENT_NAME, STUDENT_ID, etid, direction, session['user'])
		)
		### add event to student
		### get last event id
		db.query(""" SELECT id FROM events WHERE student_id=%d ORDER BY id desc LIMIT 1 """ % (STUDENT_ID))
		r = db.store_result()
		r = r.fetch_row(maxrows=1, how=1)
		last_eid = int(r[0]['id'])
		print "STUDNET SIGNIN LAST ID"
		print last_eid

		db.query(""" UPDATE students SET last_event=%d WHERE id=%d """ % (last_eid, STUDENT_ID))

	except Exception, e:
		print e
		return last_eid

	return last_eid

def get_event_name_from_id(event_id):
	db.query(""" SELECT name FROM events WHERE id=%d  """ % int(event_id))
	r = db.store_result()
	r = r.fetch_row(maxrows=1, how=1)

	return r[0]['name']

def student_signout(current_event_id, STUDENT_ID):

	event_name = get_event_name_from_id(current_event_id)
	event_type_id = get_event_type_id(event_name)
	### create signout event
	db.query(""" INSERT INTO events (name, student_id, event_type_id, direction, author) VALUES ("%s", %d, %d, "%s", "%s") """ %
		( event_name, STUDENT_ID, event_type_id, "OUT", session['user'])
	)
	### add event to student
	### get last event id
	db.query(""" SELECT id FROM events WHERE student_id=%d ORDER BY id desc LIMIT 1 """ % (STUDENT_ID))
	r = db.store_result()
	r = r.fetch_row(maxrows=1, how=1)
	last_eid = int(r[0]['id'])
	print "STUDENT SIGN OUT LAST ID"
	print last_eid

	db.query(""" UPDATE students SET last_event=%d WHERE id=%d """ % (last_eid, STUDENT_ID))



#### ROUTING

@app.route("/")
@requireLogin
def route_default():

	### note how=0 returns tuples, how=1 returns dicts
	### maxrows = 0 returns all rows
	### fetch all students
	db.query("""  SELECT * FROM students ORDER BY grade """)
	students = db.store_result()
	students = students.fetch_row(maxrows=0, how=1)
	print students

	### for each student fetch their events for today
	for student in students:
		db.query(""" SELECT * FROM events WHERE student_id=%d ORDER BY time""" % int(student["id"]))
		r = db.store_result()
		r = r.fetch_row(maxrows=0, how=1)
		student["events"] = r

	print student["events"]
	### fetch all event types
	db.query("""  SELECT * FROM event_types """)
	event_types = db.store_result()
	event_types = event_types.fetch_row(maxrows=0, how=1)
	print event_types
	
	return render_template("mainpage.html", students=students, event_types=event_types)

@app.route("/login", methods=['GET', 'POST'])
def route_login():
	if request.method == "POST":
		if "username" in request.form and "password" in request.form:
			if check_ldap_credentials(request.form["username"], request.form["password"], "10.1.5.9"):
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

@app.route("/add/student", methods=['GET', 'POST'])
@requireLogin
def route_add_student():
	if request.method == "POST":
		if "lastname" in request.form and "firstname" in request.form and "grade" in request.form:
			try:
				db.query("""INSERT INTO students (last_name, first_name, grade) VALUES ( "%s", "%s", %d )  """ % (request.form["lastname"], request.form["firstname"], int(request.form["grade"])))
				print "student added"
			except Exception, e:
				print e

	return render_template("addstudent.html")

@app.route("/add/event-type", methods=['GET', 'POST'])
@requireLogin
def route_add_event():
	if request.method == "POST":
		if "event-type" in request.form:
			try:
				db.query(""" INSERT INTO event_types (name) VALUES ( "%s" ) """ % request.form["event-type"])

			except Exception, e:
				print e

	return render_template("addevent.html")



@app.route("/event/signin", methods=["GET"])
@requireLogin
def route_event_signin():
	if request.method == "GET":
		EVENT_NAME = request.args.get("event_name")
		STUDENT_ID = int(request.args.get("student_id"))

		etid = get_event_type_id(EVENT_NAME)
		if not etid:
			abort(500)

		current_event_id = get_current_event_id(STUDENT_ID)

		if current_event_id == None:
			student_signin(EVENT_NAME, STUDENT_ID, etid)
		else:
			if get_event_direction(current_event_id) == "IN":
				flash("Student signed in already.")
				redirect(url_for("route_default"))
			else:
				flash("Signed into %s." % EVENT_NAME)
				student_signin(EVENT_NAME, STUDENT_ID, etid)


	redirect(url_for("route_default"))




@app.route("/event/signout", methods=['GET'])
@requireLogin
def route_event_signout():
	if request.method == "GET":
		STUDENT_ID = int(request.args.get("student_id"))

		### find students last event
		current_event_id = get_current_event_id(STUDENT_ID)

		if current_event_id == None:
			return "Student is already signed out."
		else:
			### create signout event
			student_signout(current_event_id, STUDENT_ID)

	return "Signed out student #%d" % STUDENT_ID 

def mark_student_absent(STUDENT_ID):
	event_type_id = get_event_type_id("ABSENT")
	db.query(""" INSERT INTO events (name, student_id, author) VALUES ("%s", %d, "%s") """ %
		( "ABSENT", STUDENT_ID, session['user'])
	)
	db.query(""" SELECT id FROM events WHERE student_id=%d ORDER BY id DESC """ % (STUDENT_ID))
	r = db.store_result()
	r = r.fetch_row(maxrows=1, how=1)
	id_of_last_event = int(r[0]['id'])

	db.query("""  UPDATE students SET last_event=%d WHERE id=%d """ % (id_of_last_event, STUDENT_ID))

@app.route("/event/absent", methods=['GET'])
@requireLogin
def route_event_absent():
	if request.method == "GET":
		STUDENT_ID = int(request.args.get("student_id"))
		mark_student_absent(STUDENT_ID)
		return "Success."
		
	return "Not success."


if __name__ == "__main__":
	#presets()

	app.debug = True
	app.run()
