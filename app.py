from flask import Flask, render_template, request, redirect, session, url_for, g
import pymysql  #flask에서 사용하는 MySQL 인터페이스
from datetime import datetime   #날짜 표시를 위한 라이브러리

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = pymysql.connect(
            host='localhost',   #MySQL Server PC 설치
            user='root',        #MySQL root 계정
            password='ajs3021502!?',    #MySQL password
            db='pybo',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db:
        db.close()


@app.route('/')
def index():
    db = get_db()   #DB 연결을 가져오는 작업. MySQL 연결(Connection) 객체
    cursor = db.cursor()    #SQL 쿼리를 실행. 일종의 SQL 실행기
    cursor.execute('''
        SELECT q.id, q.title, q.create_date, u.username
        FROM question q
        JOIN user u ON q.user_id = u.id
        ORDER BY q.id DESC
    ''')    #Question 클래스의 정보와 user 테이블에서의 id 정보를 Join
    posts = cursor.fetchall()   #ursor.fetchall(): 데이터베이스에서 실행된 쿼리의 결과를 모두 가져와서 posts에 담음
    return render_template('index.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        #request.form은 HTML 폼(form) : POST 방식으로 전송된 데이터를 받아오는 Flask의 객체
        username = request.form['username'] #요청 폼으로부터 username
        password = request.form['password'] #요청 폼으로부터 password
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute('INSERT INTO user (username, password) VALUES (%s, %s)', (username, password))
            db.commit() #INSERT 결과를 DB에 커밋. 최종반영
            return redirect(url_for('login'))
        except:
            return render_template('register.html', error='이미 존재하는 아이디입니다.')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM user WHERE username = %s', (username))
        user = cursor.fetchone()    #SQL 쿼리 실행 결과에서 단 한 개의 행(row)을 가져옴

        if user is None:
            return render_template('login.html', error='존재하지 않는 아이디입니다.')
        elif user['password'] != password:
            return render_template('login.html', error='비밀번호 오류입니다.')
        else:
            session['user_id'] = user['id']     #세션 정보에서 id 가져오기
            session['username'] = user['username']  #세션 정보에서 username 가져오기
            return redirect(url_for('index'))
        # session : Flask에서 제공하는 내장 객체로, 🔐 사용자별 로그인 상태나 정보를 서버에 저장하고 추적하기 위한 저장소
        # 파이썬의 딕셔너리처럼 동작하는 객체

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()     #세션 지우기
    return redirect(url_for('index'))


@app.route('/question/create', methods=['GET', 'POST'])
def write():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO question (title, content, user_id, create_date) VALUES (%s, %s, %s, %s)',
            (title, content, session['user_id'], datetime.now())    #Question DB에 글 INSERT
        )
        db.commit()     #데이터베이스에서 **INSERT, UPDATE, DELETE 같은 변경 작업을 실제로 저장(확정)**시키는 명령
        return redirect(url_for('index'))
    return render_template('write.html')


@app.route('/question/<int:question_id>', methods=['GET', 'POST'])
def detail(question_id):    #각 글의 detail이므로 작성자 ID가 매개변수로 전달 됨
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT q.*, u.username FROM question q JOIN user u ON q.user_id = u.id WHERE q.id = %s',
        (question_id,)
    )
    question = cursor.fetchone()    #질문은 쿼리결과 하나만

    cursor.execute(
        'SELECT a.*, u.username FROM answer a JOIN user u ON a.user_id = u.id WHERE a.question_id = %s',
        (question_id,)
    )
    answers = cursor.fetchall()     #댓글은 쿼리결과 모두
    
    if request.method == 'POST' and 'user_id' in session:
        content = request.form['content']
        cursor.execute(
            'INSERT INTO answer (content, create_date, user_id, question_id) VALUES (%s, %s, %s, %s)',
            (content, datetime.now(), session['user_id'], question_id)
        )
        db.commit() #INSERT 결과 반영
        return redirect(url_for('detail', question_id=question_id))

    return render_template('detail.html', question=question, answers=answers, session=session)


@app.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(question_id):     #몇번 글을 수정 할 것인지
    if 'user_id' not in session:    #현재 세션에 없으면 즉, 로그인이 안 되어있으면
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM question WHERE id = %s', (question_id,))
    question = cursor.fetchone()

    if question['user_id'] != session['user_id']:   #현재 세션의 사용자 즉, 로그인한 사용자가 작성자랑 다르면 수정 X
        return '수정 권한이 없습니다.', 403

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor.execute('UPDATE question SET title = %s, content = %s WHERE id = %s', (title, content, question_id))
        db.commit()
        return redirect(url_for('detail', question_id=question_id))

    return render_template('edit.html', question=question)


@app.route('/question/<int:question_id>/delete')
def delete_question(question_id):
    if 'user_id' not in session:    #로그인 된 사용자인지 확인하고
        return redirect(url_for('login'))   #아니면 로그인 하도록 유도

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM question WHERE id = %s', (question_id))
    question = cursor.fetchone()    #id에 해당하는 글 쿼리 하나만 가져오기

    if question['user_id'] != session['user_id']:   #글 쓴 사용자가 아니면
        return '삭제 권한이 없습니다.', 403

    cursor.execute('DELETE FROM question WHERE id = %s', (question_id))
    db.commit()
    return redirect(url_for('index'))


@app.route('/answer/<int:answer_id>/delete')
def delete_answer(answer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM answer WHERE id = %s', (answer_id))
    answer = cursor.fetchone()

    if answer['user_id'] != session['user_id']:
        return '댓글 삭제 권한이 없습니다.', 403

    cursor.execute('DELETE FROM answer WHERE id = %s', (answer_id))
    db.commit()
    return redirect(url_for('detail', question_id=answer['question_id']))   #삭제하고 본글 페이지로


@app.route('/answer/<int:answer_id>/edit', methods=['GET', 'POST'])
def edit_answer(answer_id):
    if 'user_id' not in session:    #로그인 여부로 수정권한 확인
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM answer WHERE id = %s', (answer_id))
    answer = cursor.fetchone()

    if answer['user_id'] != session['user_id']:
        return '댓글 수정 권한이 없습니다.', 403

    if request.method == 'POST':
        content = request.form['content']
        cursor.execute('UPDATE answer SET content = %s WHERE id = %s', (content, answer_id))
        db.commit()
        return redirect(url_for('detail', question_id=answer['question_id']))

    return render_template('edit_answer.html', answer=answer)


if __name__ == '__main__':
    app.run(debug=True)