 uwsgi -s /tmp/uwsgi.sock --module stracker2 --callable app
 chmod 777 /tmp/uwsgi.sock
