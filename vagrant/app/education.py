from flask import Flask, render_template, redirect, request, url_for, \
    flash, jsonify

# import CRUD Operations
from database_setup import Base, User, Subject, Topic, Question
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Auth imports
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Create session and connect to DB ##
engine = create_engine('sqlite:///educationmenu.db')
Base.metadata.bind = engine

session = scoped_session(sessionmaker(bind=engine))

app = Flask(__name__)

@app.route('/users')
@app.route('/users/')
def users():
    users = session.query(User)
    # return "The current session state is %s" % login_session['state']
    return render_template('users.html', users=users)

# Create anti-forgery state token
@app.route('/login')
@app.route('/login/')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    flash("you are now logged in as %s" % login_session['username'])

    def createUser(login_session):
        newUser = User(name=login_session['username'], email=login_session[
                       'email'], picture=login_session['picture'])
        session.add(newUser)
        session.commit()
        user = session.query(User).filter_by(email=login_session['email']).one()
        return(user.id)


    def getUserInfo(user_id):
        user = session.query(User).filter_by(id=user_id).one()
        return(user)


    def getUserID(email):
        try:
            user = session.query(User).filter_by(email=email).one()
            return user.id
        except:
            return(None)

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    # See if a user exists, if it doesn't make a new one

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

@app.route('/gdisconnect')
@app.route('/gdisconnect/')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return(response)
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        # Rest User's sesssion
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return(response)
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return(response)


@app.route('/')
@app.route('/education')
@app.route('/education/')
def subjects():
    subjects = session.query(Subject)
    return(render_template('subjects.html', subjects=subjects, login_session=login_session))

@app.route('/education/subject/new', methods=['GET', 'POST'])
@app.route('/education/subject/new/', methods=['GET', 'POST'])
def newSubject():
    if request.method == 'POST':
        newSubject = Subject(name=request.form['name'])
        session.add(newSubject)
        session.commit()
        flash("New subject created!")
        return(redirect(url_for('subjects')))
    else:
        return(render_template('newsubject.html'))


@app.route('/education/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@app.route('/education/subject/<int:subject_id>/edit/', methods=['GET', 'POST'])
def editSubject(subject_id):
    editSubject = session.query(Subject).filter_by(id=subject_id).one()
    if request.method == 'POST':
        editSubject.name = request.form['name']
        session.add(editSubject)
        session.commit()
        flash("Subject edited")
        return(redirect(url_for('subjects')))
    else:
        return(render_template('editsubject.html',subject=editSubject))


@app.route('/education/subject/<int:subject_id>/delete',
           methods=['GET', 'POST'])
@app.route('/education/subject/<int:subject_id>/delete/',
           methods=['GET', 'POST'])
def deleteSubject(subject_id):
    deleteSubject = session.query(Subject)\
	                .filter_by(id=subject_id).one()
    if request.method == 'POST':
        session.delete(deleteSubject)
        session.commit()
        flash("Subject deleted!")
        return(redirect(url_for('subjects')))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('deletesubject.html', subject=subject))


@app.route('/education/<int:subject_id>', methods=['GET', 'POST'])
@app.route('/education/<int:subject_id>/', methods=['GET', 'POST'])
def topics(subject_id):
    topics = session.query(Topic).filter_by(subject_id=subject_id)
    subject = session.query(Subject).filter_by(id=subject_id).one()
    return(render_template('topics.html', topics=topics, subject=subject))


@app.route('/education/<int:subject_id>/JSON')
def subjectJSON(subject_id):
    subject = session.query(Subject).filter_by(id=subject_id).one()
    topics = session.query(Topic).filter_by(subject_id=subject.id)
    return(jsonify(topics=[topics.serialize for topic in topics]))


@app.route('/education/<int:subject_id>/<int:topic>', methods=['GET', 'POST'])
@app.route('/education/<int:subject_id>/<int:topic>/', methods=['GET', 'POST'])
def topic(subject_id):
    subject = session.query(Subject).filter_by(id=subject_id).one()
    return(render_template('topic.html', subject=subject))


@app.route('/education/<int:subject_id>/topic/new', methods=['POST', 'GET'])
@app.route('/education/<int:subject_id>/topic/new/', methods=['POST', 'GET'])
def newTopic(subject_id):
    subject = session.query(Subject).filter_by(id=subject_id).one()
    if request.method == 'POST':
        newTopic = Topic(
            name=request.form['name'], description=request.form['description'],\
			subject_id=subject_id)
        session.add(newTopic)
        session.commit()
        flash("New topic created!")
        return redirect(url_for('topics', subject_id=subject_id))
    else:
        return render_template('newtopic.html', subject=subject)


@app.route('/education/<int:subject_id>/topic/<int:topic_id>/edit',
           methods=['POST', 'GET'])
@app.route('/education/<int:subject_id>/topic/<int:topic_id>/edit/',
          methods=['POST', 'GET'])
def editTopic(subject_id, topic_id):
    editTopic = session.query(Topic).filter_by(subject_id=subject_id,
                                              id=topic_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editTopic.name = request.form['name']
            editTopic.description = request.form['description']
            session.add(editTopic)
            session.commit()
            flash("Subject topic edited!")
        return(redirect(url_for('topics', subject_id=subject_id)))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('edittopic.html', subject=subject,
                               topic=editTopic))


@app.route('/education/<int:subject_id>/topic/<int:topic_id>/delete',
           methods=['POST', 'GET'])
@app.route('/education/<int:subject_id>/topic/<int:topic_id>/delete/',
          methods=['POST', 'GET'])
def deleteTopic(subject_id, topic_id):
    deleteTopic = session.query(Topic).filter_by(subject_id=subject_id,
                                                   id=topic_id).one()
    if request.method == 'POST':
        session.delete(deleteTopic)
        session.commit()
        flash("Topic deleted!")
        return(redirect(url_for('topics', subject_id=subject_id)))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('deletetopic.html', subject=subject,
                               topic=deleteTopic))

if __name__ == '__main__':
    app.secret_key = 'supersecretkey'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
