from functools import wraps
from flask import request, render_template, session, redirect, url_for
import os

def require_site_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip password check for static files
        if request.path.startswith('/static/'):
            return f(*args, **kwargs)
            
        # Skip password check if already authenticated
        if session.get('site_authenticated'):
            return f(*args, **kwargs)
            
        # If password form submitted
        if request.method == 'POST' and request.form.get('site_password'):
            if request.form['site_password'] == os.environ.get('SITE_PASSWORD'):
                session['site_authenticated'] = True
                return redirect(request.path)
            else:
                return render_template('site_password.html', error="Incorrect password")
                
        # Show password form if not authenticated
        return render_template('site_password.html')
        
    return decorated_function 