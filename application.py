from flask import Flask, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt
import re
from mysqlconnection import connectToMySQL
from datetime import datetime
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
    
app = Flask(__name__)
app.secret_key = 'keeping it secret yo'
bcrypt = Bcrypt(app)

#Homepage
@app.route('/')
def index():
    return render_template('index.html')

#Registration
@app.route('/process', methods=['POST'])
def register():
    is_valid = True

    if len(request.form['name']) < 3:
        flash('Name must be longer than 2 characters.')
        is_valid = False
    if len(request.form['userName']) < 3:
        flash('Username is not valid.')
        is_valid = False
    if len(request.form['pwd']) < 8:
        flash('Password must be at least 8 characters long')
        is_valid = False
    if request.form['pwd'] != request.form['pwd2']:
        flash('Passwords do not match.')
        is_valid = False
    
    if is_valid == False:
        return redirect('/')
    else:
        pw_hash = bcrypt.generate_password_hash(request.form['pwd'])
        mysql = connectToMySQL('travel_buddy')
        query = 'INSERT INTO users (name, username, password, created_at, updated_at) VALUES (%(n)s,%(un)s,%(pw)s,NOW(), NOW())'
        data = {
            'n': request.form['name'],
            'un': request.form['userName'],
            'pw': pw_hash
        }

        user = mysql.query_db(query, data)
        session['userID'] = user
        session['greeting'] = request.form['userName']

        return redirect('/trips')

#login
@app.route('/login', methods=['POST'])
def login():
    mysql = connectToMySQL('travel_buddy')
    query = 'select * from users where username = %(un)s'
    data = {
        'un': request.form['logUserName']
    }
    result = mysql.query_db(query, data)

    if result:
        if bcrypt.check_password_hash(result[0]['password'], request.form['logPwd']):
            session['userID'] = result[0]['id']
            session['greeting'] = result[0]['username']
            return redirect('/trips')
        else:
            flash('UserName or Password are incorrect')
    else:
        flash('User not found.')

    return redirect('/')

@app.route('/trips')
def trips():
    if not 'userID' in session:
        return redirect('/')
    else:

        #Trips the User has made
        mysql = connectToMySQL('travel_buddy')
        query = "select * from trips as t join users_has_trips as uht on uht.trips_id = t.id where uht.users_id = %(un)s"
        data = {
            'un': session['userID']
        }
        users_own_trips = mysql.query_db(query,data)

        #Available trips to join
        mysql = connectToMySQL('travel_buddy')
        query = "select * from trips as t join users as u on u.id = t.users_id where t.users_id != %(un)s and not exists (select * from users_has_trips as uht where uht.trips_id = t.id and uht.users_id = %(un)s)"
        data = {
            'un': session['userID']
        }
        user_trips = mysql.query_db(query,data)
   
        return render_template('travel.html', user_trips = user_trips, users_own_trips = users_own_trips)

@app.route('/addtrip')
def addtrip():
    return render_template('/addtrip.html')

@app.route('/saveTrip', methods=['POST'])
def savetrip():
    start = datetime.strptime(request.form['start'],"%Y-%m-%dT%H:%M")
    end = datetime.strptime(request.form['end'],"%Y-%m-%dT%H:%M")
    
    is_valid = True

    if len(request.form['destination']) < 1:
        flash('Destination must have an entry')
        is_valid = False
    if len(request.form['description']) < 1:
        flash('Description required.')
        is_valid = False
    if start > end:
        flash('The trip must have a start date earlier than the end date.')
        is_valid = False

    if is_valid == False:
        return redirect('/addtrip')
    else:
        mysql = connectToMySQL('travel_buddy')
        query = "insert into trips (start, end, description, destination, created_at, updated_at, users_id) values (%(s)s, %(e)s, %(desc)s, %(dest)s, NOW(), NOW(), %(uid)s)"
        data = {
            's': start,
            'e': end,
            'desc': request.form['description'],
            'dest': request.form['destination'],
            'uid': session['userID'],
        }
        tid = mysql.query_db(query, data)

        mysql = connectToMySQL('travel_buddy')
        query = "insert into users_has_trips (users_id, trips_id) values (%(user_id)s, %(trip_id)s)"
        data = {
            'user_id': session['userID'],
            'trip_id': tid
        }
        mysql.query_db(query,data)
        return redirect('/trips')

@app.route('/destination/<id>')
def destination(id):
    
    mysql = connectToMySQL('travel_buddy')
    query = "select * from trips join users as u on u.id = trips.users_id where trips.id = %(tid)s"
    data = {
        'tid': id
    }
    trip_info = mysql.query_db(query, data)

    mysql = connectToMySQL('travel_buddy')
    query = "select distinct u.username from trips as t join users_has_trips as uht on uht.trips_id = t.id or uht.users_id = t.users_id join users as u on u.id = uht.users_id where t.id = %(tid)s and uht.users_id !=%(uid)s"
    data = {
        'uid': session['userID'],
        'tid': id
    }
    users_going = mysql.query_db(query, data)

    return render_template('/destination.html', trip_info = trip_info , users_going = users_going)


@app.route('/join/<id>')
def joinTrip(id):
    print(id)
    mysql = connectToMySQL('travel_buddy')
    query = "insert into users_has_trips (users_id, trips_id) values (%(uid)s, %(tid)s)"
    data  = {
        'uid': session['userID'],
        'tid': id
    }
    mysql.query_db(query, data)
    return redirect('/trips')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)