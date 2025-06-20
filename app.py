from flask import Flask, render_template, request, redirect, session, url_for, g
import pymysql  # flask에서 사용하는 MySQL 인터페이스
from datetime import datetime  # 날짜 표시를 위한 라이브러리

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = pymysql.connect(
            host='localhost',  # MySQL Server PC 설치
            user='root',        # MySQL root 계정
            password='ajs3021502!?',  # MySQL password
            db='pybo',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    return db


@app.teardown_appcontext  # Flask가 앱 컨텍스트(AppContext)를 종료할 때 호출되는 후처리 함수
                          # 매 HTTP 요청이 끝나면 자동 실행됨
def close_connection(exception):
    db = getattr(g, '_database', None)  # get_db() 함수에서 g._database에 저장해놓은 DB 연결 객체를 꺼냄
    if db:
        db.close()  # DB 연결 close()


@app.route('/')
def index():
    db = get_db()  # DB 연결을 가져오는 작업. MySQL 연결(Connection) 객체
    cursor = db.cursor()  # SQL 쿼리를 실행. 일종의 SQL 실행기
    cursor.execute('''
        SELECT q.id, q.title, q.create_date, u.username
        FROM question q
        JOIN user u ON q.user_id = u.id
        ORDER BY q.id DESC
    ''')  # Question 테이블과 user 테이블을 JOIN
    posts = cursor.fetchall()  # 쿼리 결과 전체를 리스트 형태로 가져옴
    return render_template('index.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # request.form은 HTML 폼(form): POST 방식으로 전송된 데이터를 받아오는 Flask의 객체
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute('INSERT INTO user (username, password) VALUES (%s, %s)', (username, password))
            db.commit()  # INSERT 결과를 DB에 커밋. 최종 반영
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
        cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
        user = cursor.fetchone()  # 쿼리 결과 중 첫 번째 한 행만 반환

        if user is None:
            return render_template('login.html', error='존재하지 않는 아이디입니다.')
        elif user['password'] != password:
            return render_template('login.html', error='비밀번호 오류입니다.')
        else:
            session['user_id'] = user['id']  # 세션에 사용자 ID 저장
            session['username'] = user['username']  # 세션에 사용자 이름 저장
            return redirect(url_for('index'))
            # session은 Flask에서 제공하는 딕셔너리 같은 객체로, 사용자별 상태 유지에 사용됨

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()  # 세션 초기화
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
            (title, content, session['user_id'], datetime.now())
        )
        db.commit()  # INSERT 결과를 실제 DB에 반영
        # 글 등록 후 JavaScript alert 창을 띄운 뒤, 메인 페이지('/')로 자동 이동
        return '''<script>alert("글이 등록되었습니다."); window.location="/";</script>'''
    return render_template('write.html')


@app.route('/question/<int:question_id>', methods=['GET', 'POST'])
def detail(question_id):  # 글 상세보기
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT q.*, u.username FROM question q JOIN user u ON q.user_id = u.id WHERE q.id = %s',
        (question_id)
    )
    question = cursor.fetchone()  # 질문 하나만 가져옴

    cursor.execute(
        'SELECT a.*, u.username FROM answer a JOIN user u ON a.user_id = u.id WHERE a.question_id = %s',
        (question_id)
    )
    answers = cursor.fetchall()  # 답변(댓글)은 여러 개 가져옴

    if request.method == 'POST' and 'user_id' in session:
        content = request.form['content']
        cursor.execute(
            'INSERT INTO answer (content, create_date, user_id, question_id) VALUES (%s, %s, %s, %s)',
            (content, datetime.now(), session['user_id'], question_id)
        )
        db.commit()
        # 댓글 작성 후 알림창을 띄우고, 현재 글 상세 페이지로 이동
        return '''<script>alert("댓글이 등록되었습니다."); window.location="/question/%d";</script>''' % question_id
    
    return render_template('detail.html', question=question, answers=answers, session=session)


@app.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(question_id):  # 글 수정
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM question WHERE id = %s', (question_id))
    question = cursor.fetchone()

    if question['user_id'] != session['user_id']:  # 작성자 본인인지 확인
        return '수정 권한이 없습니다.', 403
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor.execute('UPDATE question SET title = %s, content = %s WHERE id = %s', (title, content, question_id))
        db.commit()
        return redirect(url_for('detail', question_id=question_id))
    
    return render_template('edit.html', question=question)


@app.route('/question/<int:question_id>/delete')
def delete_question(question_id):  # 글 삭제
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM question WHERE id = %s', (question_id))
    question = cursor.fetchone()

    if question['user_id'] != session['user_id']:  # 작성자 본인인지 확인
        return '삭제 권한이 없습니다.', 403

    cursor.execute('DELETE FROM question WHERE id = %s', (question_id))
    db.commit()
    return '''<script>alert("질문이 삭제되었습니다."); window.location="/";</script>'''


@app.route('/answer/<int:answer_id>/delete')
def delete_answer(answer_id):  # 댓글 삭제
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM answer WHERE id = %s', (answer_id))
    answer = cursor.fetchone()

    if answer['user_id'] != session['user_id']:  # 작성자 본인인지 확인
        return '댓글 삭제 권한이 없습니다.', 403

    cursor.execute('DELETE FROM answer WHERE id = %s', (answer_id))
    db.commit()
    return '''<script>alert("댓글이 삭제되었습니다."); window.location="/question/%d";</script>''' % answer['question_id']


@app.route('/answer/<int:answer_id>/edit', methods=['GET', 'POST'])
def edit_answer(answer_id):  # 댓글 수정
    if 'user_id' not in session:
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
        return '''<script>alert("댓글이 수정되었습니다."); window.location="/question/%d";</script>''' % answer['question_id']

    return render_template('edit_answer.html', answer=answer)


if __name__ == '__main__':
    app.run(debug=True)