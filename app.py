import os
import sys
from flask import Flask, render_template, request, jsonify, flash, send_from_directory
from pandas import read_excel, read_sql_query
from datetime import datetime
from pytz import timezone
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView


bangkok = timezone('Asia/Bangkok')

db = SQLAlchemy()
admin = Admin()

def create_app():
    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'static')
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qrscan.db'
    app.config['SECRET_KEY'] = 'mumtfightcovid19'
    db.init_app(app)
    with app.app_context():
        db.create_all()
    admin.init_app(app)
    return app


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column('id', db.String(), primary_key=True)
    firstname = db.Column('firstname', db.String(), nullable=False)
    lastname = db.Column('lastname', db.String(), nullable=False)

    def __init__(self, id, firstname, lastname):
        self.id = id
        self.firstname = firstname
        self.lastname = lastname

    @property
    def fullname(self):
        return u'{} {}'.format(self.firstname, self.lastname)

    def __str__(self):
        return '{}: {}'.format(self.id, self.fullname)


class CheckIn(db.Model):
    __tablename__ = 'checkin_records'
    id = db.Column('id', db.Integer(), primary_key=True, autoincrement=True)
    checked_at = db.Column('checked_at', db.DateTime(timezone=True), nullable=False)
    user_id = db.Column('user_id', db.String(), db.ForeignKey('users.id'))
    user = db.relationship(User, backref=db.backref('checkin_records'))


app = create_app()


class UploadUserView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if request.method == 'POST':
            filename = request.files.get('fileUpload')
            if filename is None:
                flash('No file given.')
            else:
                df = read_excel(filename)
                num_added = 0
                for idx,row in df.iterrows():
                    existing_user = User.query.get(str(row[0]))
                    if not existing_user:
                        new_user = User(row[0], row[1], row[2])
                        db.session.add(new_user)
                        num_added += 1
                db.session.commit()
                flash('New {} users added successfully.'.format(num_added))
        return self.render('upload_users.html')


class ExportView(BaseView):
    @expose('/', methods=['GET'])
    def index(self):
        return self.render('export.html')

    @expose('/export', methods=['GET'])
    def export(self):
        df = read_sql_query('SELECT * FROM checkin_records INNER JOIN users ON users.id=checkin_records.user_id;',
                            con=db.engine, parse_dates=['checked_at'])
        df.to_excel('export.xlsx', index=None)
        flash('Export successfully.')
        return send_from_directory(os.getcwd(), 'export.xlsx')


admin.add_view(UploadUserView(name="Upload", endpoint='upload'))
admin.add_view(ExportView(name="Export", endpoint='export'))


class UserAdminView(ModelView):
    form_columns = ('id', 'firstname', 'lastname')
    column_list = ('id', 'firstname', 'lastname')


admin.add_view(UserAdminView(User, db.session))
admin.add_view(ModelView(CheckIn, db.session))

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/scan', methods=['POST'])
def read_cord():
    content = request.json
    user = User.query.filter_by(id=content['code']).first()
    if user:
        try:
            record = CheckIn()
            record.user = user
            record.checked_at = datetime.now(tz=bangkok)
            db.session.add(record)
            db.session.commit()
        except:
            return {'error': 'Failed to save to the database.'}
        else:
            return {'checked_in': datetime.now(tz=bangkok), 'code': content['code'], 'name': user.fullname}
    else:
        return {'error': 'Cannot find the user with that ID.'}


if __name__ == '__main__':
    app.run(debug=True)
