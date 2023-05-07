from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, TypeDecorator, VARCHAR, Float
from sqlalchemy import update
import json
from privacy import USER, PW, URL, PORT, DB

engine = create_engine("postgresql://{}:{}@{}:{}/{}".format(USER, PW, URL, PORT, DB))
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

# custom type
class ListType(TypeDecorator):
    impl = VARCHAR
    cache_ok = True

    # 'process_bind_param' method is used to convert the list to a JSON string
    # before it is inserted into the database
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
    
    # 'process_result_value' method is used to convert the JSON string back to a list
    # when it is retrieved from the database
    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        
    def process_literal_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
    

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    passwd = Column(String(50), nullable=False)
    recommendation = Column(Float)
    dietTable = Column(ListType)

    def __init__(self, name=None, passwd=None, recommendation=None, dietTable=None):
        self.name = name
        self.passwd = passwd
        if recommendation is not None:
            self.recommendation = recommendation
        else:
            self.recommendation = 0

        if dietTable is not None:
            self.dietTable = dietTable
        else:
            self.dietTable = []

    def __repr__(self):
        return f'<User {self.name!r}>'

# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


from flask import Flask
from flask import request
from flask import jsonify
from werkzeug.serving import WSGIRequestHandler

WSGIRequestHandler.protocol_version = "HTTP/1.1"

app = Flask(__name__)

@app.route("/", methods=['GET'])
def check_server():
    return jsonify({'code':200, 'msg':'success'})

@app.route("/adduser", methods=['POST'])
def add_user():
    content = request.get_json(silent=True)
    name = content["name"]
    passwd = content["passwd"]
    if db_session.query(User).filter_by(name=name).first() is None:
        u = User(name=name, passwd=passwd, recommendation=0, dietTable=[])
        db_session.add(u)
        db_session.commit()
        return jsonify(success=True)
    else:
        return jsonify(success=False)

@app.route("/login", methods=['POST'])
def login():
    content = request.get_json(silent=True)
    name = content["name"]
    passwd = content["passwd"]

    check = False
    result = db_session.query(User).all()
    for i in result:
        if i.name == name and i.passwd == passwd:
            check = True
    return jsonify(success=check)

@app.route("/select_property", methods=['POST'])
def select_property():
    content = request.get_json(silent=True)
    name = content["name"]
    recommendation = content["recommendation"]

    user = db_session.query(User).filter_by(name=name).first()
    user.recommendation = recommendation

    db_session.execute(update(User).where(User.name==name).values(recommendation=user.recommendation))
    db_session.commit()
    return jsonify(success=True)

@app.route("/addfoodInfo", methods=['POST'])
def add_food():
    content = request.get_json(silent=True)
    name = content["name"]
    date = content["date"]
    food = content["food"]
    calorie = content["calorie"]

    check = False

    user = db_session.query(User).filter_by(name=name).first()
    if user.dietTable is None:
        user.dietTable = []
    
    for dayInfo in user.dietTable:
        if dayInfo[0] == date:
            dayInfo[1][food] = calorie
            # dayInfo[1].append(food)
            dayInfo[2] += calorie
            check = True
    
    if check == False:
        user.dietTable.append([date, {food:calorie}, calorie])
        check = True

    db_session.execute(update(User).where(User.name==name).values(dietTable=user.dietTable))
    db_session.commit()
    return jsonify(success=check)
                    
@app.route("/getfoodInfo", methods=['POST'])
def get_foodInfo():
    content = request.get_json(silent=True)
    name = content["name"]
    date = content["date"]

    user = db_session.query(User).filter_by(name=name).first()
    for dayInfo in user.dietTable:
        if dayInfo[0] == date:
            return jsonify(dayInfo)
    return jsonify(success=False)

@app.route("/getRecommendation", methods=['POST'])
def get_recommendation():
    content = request.get_json(silent=True)
    name = content["name"]

    user = db_session.query(User).filter_by(name=name).first()
    return jsonify(user.recommendation)


if __name__ == "__main__":
    app.run(host='localhost', port=8888)
