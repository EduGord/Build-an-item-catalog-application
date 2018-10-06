from flask import Flask, render_template, redirect, request, url_for, \
    flash, jsonify

# import CRUD Operations
from database_setup import Base, Subject, Topic, Question
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Create session and connect to DB ##
engine = create_engine('sqlite:///educationmenu.db')
Base.metadata.bind = engine

session = scoped_session(sessionmaker(bind=engine))

app = Flask(__name__)


@app.route('/')
@app.route('/education')
@app.route('/education/')
def subjectsList():
    subjects = session.query(Subject)
    return(render_template('subjectslist.html', subjects=subjects))


@app.route('/education/subject/new', methods=['GET', 'POST'])
@app.route('/education/subject/new/', methods=['GET', 'POST'])
def newSubject():
    if request.method == 'POST':
        newSubject = Subject(name=request.form['name'])
        session.add(newSubject)
        session.commit()
        flash("New subject created!")
        return(redirect(url_for('subjectsList')))
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
        return(redirect(url_for('subjectsList')))
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
        return(redirect(url_for('subjectsList')))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('deletesubject.html', subject=subject))


@app.route('/education/<int:subject_id>', methods=['GET', 'POST'])
@app.route('/education/<int:subject_id>/', methods=['GET', 'POST'])
def subjectTopics(subject_id):
    topics = session.query(Topic).filter_by(subject_id=subject_id)
    subject = session.query(Subject).filter_by(id=subject_id).one()
    return(render_template('subject.html', topics=topics, subject=subject))


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
        return redirect(url_for('subjectTopics', subject_id=subject_id))
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
        return(redirect(url_for('subjectTopics', subject_id=subject_id)))
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
        return(redirect(url_for('subjectTopics', subject_id=subject_id)))
    else:
        subject = session.query(Subject).filter_by(id=subject_id).one()
        return(render_template('deletetopic.html', subject=subject,
                               topic=deleteTopic))

if __name__ == '__main__':
    app.secret_key = 'supersecretkey'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
