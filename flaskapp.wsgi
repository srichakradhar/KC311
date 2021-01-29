#flaskapp.wsgi
import sys
sys.path.insert(0, '/var/www/html/kc311')

from app import app as application