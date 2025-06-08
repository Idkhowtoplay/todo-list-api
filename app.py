from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("database")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.getenv("modification")
app.config["SECRET_KEY"] = os.getenv("secret_key")
app.config["JWT_SECRET_KEY"] = os.getenv("jwt_key")
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.json.sort_keys = False

db = SQLAlchemy(app)
jwt = JWTManager(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(90), nullable=False)
    email = db.Column(db.String(90), unique=True, nullable=False)
    password_hash = db.Column(db.String(90), nullable=False)
    todos = db.relationship("Todo", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(90), nullable=False)
    description = db.Column(db.String(90), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return "home"

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        if not data or "name" not in data or "email" not in data or "password" not in data:
            raise ValueError("name, email and password required")
        user = User(name=data["name"], email=data["email"])
        user.set_password(data["password"])
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=user.id)
        return jsonify({"token": token}), 200
    
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data["email"]).first()
        token = create_access_token(identity=user.id)

        if user and user.check_password(data["password"]):
            return jsonify({"token": token})
        else:
            return jsonify("email or password is invalid")
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route("/todos", methods=["POST"])
@jwt_required()
def todo():
    try:
        user_id = get_jwt_identity()
        user = User.query.filter_by(id=user_id).first()

        if user:
            data = request.get_json()
            if not data or "title" not in data or "description" not in data:
                raise ValueError("title and description are required")
            todo = Todo(title=data["title"], description=data["description"], user_id=user_id)
            db.session.add(todo)
            db.session.commit()

            return jsonify({
                "id": todo.id,
                "title": todo.title,
                "description": todo.description
            }), 200
    
    
    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@app.route("/todos/<int:id>", methods=["PUT"])
@jwt_required()
def update(id):
    user_id = get_jwt_identity()
    todo = Todo.query.get(id)

    if not todo:
        return jsonify({"message": "not found"})

    if todo.user_id != user_id:
        return jsonify({"message": "Forbidden"}), 403
    
    data = request.get_json()
    if not data or "title" not in data or "description" not in data:
        raise ValueError("title and description requqired")
    todo.title = data["title"]
    todo.description = data["description"]
    db.session.commit()

    return jsonify({
        "id": todo.id,
        "title": todo.title,
        "description": todo.description
    })
    
@app.route("/todos/<int:id>", methods=["DELETE"])
@jwt_required()
def delete(id):
    user_id = get_jwt_identity()
    todo = Todo.query.get(id)

    if not todo:
        return jsonify({"message": "todo not found"})

    if todo.user_id != user_id:
        return jsonify({"message": "Forbidden"}), 403
    
    db.session.delete(todo)
    db.session.commit()
    return jsonify({
        "message": "succes"
    }), 204

@app.route("/todos", methods=["GET"])
@jwt_required()
def get():
    page = request.args.get("page", type=int)
    per_page = request.args.get("limit", type=int)
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"message": "Invalid token"})

    todo = Todo.query.paginate(page=page, per_page=per_page)
    return jsonify({
        "data": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description
            } for t in todo ],
        "page": todo.page,
        "limit": per_page,
        "total": todo.total
    })
    
   
if __name__ == '__main__':
    app.run(debug=True)
            