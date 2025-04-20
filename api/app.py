from flask import Flask, jsonify, request
from bson.objectid import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
from functools import wraps
from flask_cors import CORS
import datetime
import bcrypt
import random
import jwt
import os

load_dotenv()

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

mongodb_uri = os.getenv("MONGODB_URI")
blog_db_name = os.getenv('BLOG_DB')
jwt_secret = os.getenv("JWT_SECRET")

if not mongodb_uri or not blog_db_name:
    raise ValueError("MONGODB_URI and BLOG_DB must be set in the environment variables.")

# Connect to MongoDB
client = MongoClient(mongodb_uri)
db = client[blog_db_name]
entries_collection = db['entries']
users_collection = db['users']
codes_collection = db['codes']
activities_collection = db['activities']

# Home route.
@app.route('/')
def home():
    return """
    Welcome to Hisaab API!

    For full documentation and usage details, please visit:
    https://github.com/asdhamidi/hisaab-api

    Happy trails!
    """

# Decorator for route protection.
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token is missing!"}), 401
        token = token[7:]
        current_user = ""
        try:
            data = jwt.decode(token, jwt_secret, algorithms=["HS256"])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 401

        return f(current_user, *args, **kwargs)
    return decorator

# Authentication endpoints
@app.route('/register', methods=['POST'])
def register():
    user_data = request.json
    username = user_data.get("username")
    password = user_data.get("password")
    register_code = user_data.get("register_code")

    if not username or not password or not register_code:
        return jsonify({"message": "Username, password, and registration code are required"}), 400

    if users_collection.find_one({"username": username}):
        return jsonify({"message": "Username already exists"}), 400
    # Verify the registration code
    code_entry = codes_collection.find_one({"code": register_code})

    if not code_entry:
        return jsonify({"message": "Invalid registration code"}), 400

    # Hash the password and store the new user
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    new_user = {
        "_id": ObjectId(),
        "username": username,
        "password": hashed_password,
        "admin": false,
        "created_at": datetime.datetime.now().strftime("%-d/%-m/%-y %-I:%M %p")
    }

    users_collection.insert_one(new_user)
    print("New User Registered: ", str(new_user))
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    login_data = request.json
    username = login_data.get("username")
    password = login_data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    user = users_collection.find_one({"username": username})
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        token = jwt.encode({"username": username}, jwt_secret, algorithm="HS256")
        print(username, " Logged in")
        
        activity = {
            "_id": ObjectId(),
            "user": username,
            "date": datetime.datetime.now().strftime("%-d/%-m/%-y"),
            "activity": "logged in",
            "created_at": datetime.datetime.now().strftime("%-I:%M %p - %-d/%-m/%-y")
        }
        activities_collection.insert_one(activity)
        return jsonify({"message": "Login successful", "token": token}), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401


# Protected endpoints
@app.route('/generate_code', methods=['POST'])
@token_required
def generate_code():
    new_code = {
        "_id": ObjectId(),
        "code": str(random.randint(100000, 999999)),  # Generate a random 6-byte code
        "created_at": datetime.datetime.now().strftime("%-d/%-m/%-y %-I:%M %p")
    }
    codes_collection.insert_one(new_code)
    return jsonify({"message": "Registration code generated", "code": new_code["code"]}), 201


@app.route('/entries', methods=['GET'])
@token_required
def get_entries(current_user):
    entries = list(entries_collection.aggregate([
    {
        "$addFields": {
            "dateParts": { 
                "$split": ["$date", "/"]  # Split the date string into [day, month, year]
            }
        }
    },
    {
        "$addFields": {
            "convertedDate": {
                "$dateFromString": {
                    "dateString": {
                        "$concat": [
                            { "$arrayElemAt": ["$dateParts", 2] },  # Year
                            "-",
                            {
                                "$cond": {  # Add zero padding for the month if necessary
                                    "if": { "$lte": [{ "$strLenCP": { "$arrayElemAt": ["$dateParts", 1] } }, 1] },
                                    "then": { "$concat": ["0", { "$arrayElemAt": ["$dateParts", 1] }] },
                                    "else": { "$arrayElemAt": ["$dateParts", 1] }
                                }
                            },
                            "-",
                            {
                                "$cond": {  # Add zero padding for the day if necessary
                                    "if": { "$lte": [{ "$strLenCP": { "$arrayElemAt": ["$dateParts", 0] } }, 1] },
                                    "then": { "$concat": ["0", { "$arrayElemAt": ["$dateParts", 0] }] },
                                    "else": { "$arrayElemAt": ["$dateParts", 0] }
                                }
                            }
                        ]
                    },
                    "format": "%Y-%m-%d"
                }
            }
        }
    },
    {
        "$sort": { "convertedDate": -1 }  # Sort by the converted date in descending order (latest to oldest)
    },
    {
        "$project": {
            "_id": 1,
            "date": 1,
            "items": 1,
            "price": 1,
            "paid_by": 1,
            "notes": 1,
            "owed_all": 1,
            "owed_by": 1,
            "updated_at": 1,
            "created_at": 1,
            "previous_versions": 1
        }
    }
]))

    for entry in entries:
        entry['_id'] = str(entry['_id'])
        
    activity = {
            "_id": ObjectId(),
            "user": current_user,
            "date": datetime.datetime.now().strftime("%-d/%-m/%-y"),
            "activity": "opened Hisaab",
            "created_at": datetime.datetime.now().strftime("%-I:%M %p - %-d/%-m/%-y")
        }
    activities_collection.insert_one(activity)
    return jsonify(entries)

@app.route('/activities/<string:month>', methods=['GET'])
@token_required
def get_activities(current_user, month):
    print(current_user + " retrieved activities.")
    
    # Ensure that the month is handled without needing zero-padding
    activities = list(activities_collection.aggregate([
        {
            "$match": {
                "date": { "$regex": f'^\\d{{1,2}}/{month}/\\d{{2}}' }  # Match activities for the given month
            }
        },
        {
            "$addFields": {
                "dateParts": { 
                    "$split": ["$date", "/"]  # Split the date string into [day, month, year]
                }
            }
        },
        {
            "$addFields": {
                "convertedDate": {
                    "$dateFromString": {
                        "dateString": {
                            "$concat": [
                                { "$arrayElemAt": ["$dateParts", 2] },  # Year
                                "-",
                                {
                                    "$cond": {  # Add zero padding for the month if necessary
                                        "if": { "$lte": [{ "$strLenCP": { "$arrayElemAt": ["$dateParts", 1] } }, 1] },
                                        "then": { "$concat": ["0", { "$arrayElemAt": ["$dateParts", 1] }] },
                                        "else": { "$arrayElemAt": ["$dateParts", 1] }
                                    }
                                },
                                "-",
                                {
                                    "$cond": {  # Add zero padding for the day if necessary
                                        "if": { "$lte": [{ "$strLenCP": { "$arrayElemAt": ["$dateParts", 0] } }, 1] },
                                        "then": { "$concat": ["0", { "$arrayElemAt": ["$dateParts", 0] }] },
                                        "else": { "$arrayElemAt": ["$dateParts", 0] }
                                    }
                                }
                            ]
                        },
                        "format": "%Y-%m-%d"
                    }
                }
            }
        },
        {
            "$sort": { "convertedDate": -1 }  # Sort by the converted date in descending order (latest to oldest)
        },
        {
            "$project": {
                "_id": 1,
                "user": 1,
                "activity": 1,
                "created_at": 1
            }
        }
    ]))
    
    if users_collection.find_one({"username": current_user})["admin"] == False:
        activities = [ac for ac in activities if ac["user"] != current_user]

    for activity in activities:
        activity['_id'] = str(activity['_id'])  # Convert ObjectId to string for JSON serialization

    return jsonify(activities)

@app.route('/stats/daily_person/<string:month>', methods=['GET'])
@token_required
def daily_stats_person(user, month):
    if not month:
        return jsonify({"error": "Month is required"}), 400

    pipeline = [
        {
            '$match': {
                'date': { '$regex': f'^\\d{{1,2}}/{month}/\\d{{2}}' }
            }
        },
        {
            '$addFields': {
                'price': {'$toDouble': '$price'}
            }
        },
        {
            '$group': {
                '_id': '$paid_by',
                'total_price': {'$sum': '$price'}
            }
        },
        {
            '$sort': {'_id': -1}
        }
    ]

    aggregated_results = list(entries_collection.aggregate(pipeline))

    return jsonify(aggregated_results)

@app.route('/stats/daily/<string:month>', methods=['GET'])
@token_required
def daily_stats(user, month):
    month = int(month)
    if not month or not (1 <= month <= 12):
        return jsonify({"error": "Month is required and should be between 1 and 12"}), 400

    month_str = f'{month}'
    pipeline = [
        {
            '$match': {
                'date': { '$regex': f'^\\d{{1,2}}/{month_str}/\\d{{2}}' }
            }
        },
        {
            '$addFields': {
                'price': {'$toDouble': '$price'}
            }
        },
        {
            '$group': {
                '_id': '$date',
                'total_price': {'$sum': '$price'}
            }
        },
        {
            '$sort': {'_id': -1}
        }
    ]

    # Execute the aggregation pipeline on the collection
    aggregated_data = list(entries_collection.aggregate(pipeline))

    # Convert ObjectId to string for JSON serialization
    for entry in aggregated_data:
        if '_id' in entry:
            entry['_id'] = str(entry['_id'])

    return jsonify(aggregated_data)


@app.route('/users', methods=['GET'])
@token_required
def get_users(user):
    users = list(users_collection.find({}, {'username': 1}))
    users_list = []
    for entry in users:
        users_list.append(entry["username"])
    return users_list

@app.route('/entries/<string:id>', methods=['GET'])
@token_required
def get_entry_by_id(id):
    entry = entries_collection.find_one({'_id': ObjectId(id)}, {'_id': 1, 'date': 1, 'items': 1, 'price': 1, 'paid_by': 1, 'notes': 1, 'owed_all': 1, 'owed_by': 1, 'updated_at': 1 })

    if entry:
        entry['_id'] = str(entry['_id'])
        return jsonify(entry)
    else:
        return jsonify({"message": "entry not found"}), 404

@app.route('/entries', methods=['POST'])
@token_required
def create_entry(current_user):
    entry_data = request.json

    new_entry = {
        "_id": ObjectId(),
        "date": datetime.datetime.now().strftime("%-d/%-m/%-y") if entry_data.get('date') == "" else datetime.datetime.strptime(entry_data.get('date'), "%Y-%m-%d").strftime("%-d/%-m/%-y"),
        "items": entry_data.get("items"),
        "paid_by": current_user.strip().lower(),
        "price": entry_data.get("price"),
        "owed_all": entry_data.get("owed_all"),
        "owed_by": entry_data.get("owed_by"),
        "notes": entry_data.get("notes"),
        "updated_at": "",
        "previous_versions": [],
        "created_at": datetime.datetime.now().strftime("%-I:%M %p - %-d/%-m/%-y"),  # Store the username of the creator
        "created_by": current_user  # Store the username of the creator
    }

    entries_collection.insert_one(new_entry)
    activity = {
        "_id": ObjectId(),
        "user": current_user,
        "date": datetime.datetime.now().strftime("%-d/%-m/%-y"),
        "activity": "created a new entry for "+entry_data.get("items"),
        "created_at": new_entry["created_at"]
    }
    activities_collection.insert_one(activity)
    new_entry["_id"] = str(new_entry["_id"])

    print(current_user + " made an entry "+str(new_entry))
    return jsonify({"message": "Entry created successfully", "entry": new_entry}), 201

@app.route('/entries/<string:id>', methods=['PUT'])
@token_required
def update_entry(current_user, id):
    entry_id = ObjectId(id)
    entry = entries_collection.find_one({'_id': entry_id})

    if not entry:
        return jsonify({"message": "Entry not found"}), 404

    if entry['created_by'] != current_user:
        return jsonify({"message": "You are not authorized to edit this entry"}), 403

    entry_data = request.json

    # Handle the previous_versions properly
    previous_versions = entry.get("previous_versions", [])
    if not previous_versions:
        previous_versions = []

    # Add the current state of the entry to previous_versions before updating
    previous_versions.append({
        "_id": str(entry["_id"]),
        "date": entry.get("date", ""),
        "items": entry.get("items", ""),
        "paid_by": entry.get("paid_by", ""),
        "price": entry.get("price", ""),
        "owed_all": entry.get("owed_all", False),
        "owed_by": entry.get("owed_by", []),
        "notes": entry.get("notes", ""),
        "updated_at": entry.get("updated_at", ""),
        "created_at": entry.get("created_at", ""),
        "created_by": entry.get("created_by", "")
    })

    new_date = entry["date"]
    if entry.get("date", "") != entry_data.get("date"):
        new_date = datetime.datetime.strptime(entry_data.get('date'), "%Y-%m-%d").strftime("%-d/%-m/%-y")

    # Prepare the updated entry data
    updated_entry = {
        "updated_at": datetime.datetime.now().strftime("%-I:%M %p - %-d/%-m/%-y"),
        "items": entry_data.get("items"),
        "paid_by": entry_data.get("paid_by"),
        "date": new_date,
        "price": entry_data.get("price"),
        "owed_all": entry_data.get("owed_all"),
        "notes": entry_data.get("notes"),
        "owed_by": entry_data.get("owed_by"),
        "created_at": entry_data.get("created_at"),
        "previous_versions": previous_versions
    }

    result = entries_collection.update_one({"_id": entry_id}, {"$set": updated_entry})
    print(current_user, "updated the entry", entry)
    activity = {
        "_id": ObjectId(),
        "user": current_user,
        "date": datetime.datetime.now().strftime("%-d/%-m/%-y"),
        "activity": "updated entry for "+entry_data.get("items"),
        "created_at": updated_entry["updated_at"]
    }
    activities_collection.insert_one(activity)

    if result.matched_count == 0:
        return jsonify({"message": "No entry updated, it may not exist"}), 404

    updated_entry['_id'] = str(entry_id)
    print(current_user + " updated an entry "+str(update_entry))
    return jsonify({"message": "Entry updated successfully", "entry": updated_entry}), 200

@app.route('/entries/<string:id>', methods=['DELETE'])
@token_required
def delete_entry(current_user, id):
    entry_id = ObjectId(id)
    entry = entries_collection.find_one({'_id': entry_id})

    if not entry:
        return jsonify({"message": "Entry not found"}), 404

    if entry['created_by'] != current_user:
        return jsonify({"message": "You are not authorized to delete this entry"}), 403

    result = entries_collection.delete_one({"_id": entry_id})

    activity = {
        "_id": ObjectId(),
        "user": current_user,
        "date": datetime.datetime.now().strftime("%-d/%-m/%-y"),
        "activity": "deleted entry for "+entry.get("items"),
        "created_at": datetime.datetime.now().strftime("%-I:%M %p - %-d/%-m/%-y")
    }
    activities_collection.insert_one(activity)

    if result.deleted_count > 0:
        return jsonify({"message": "Entry deleted successfully"})
    else:
        return jsonify({"message": "Entry not found"}), 404

@app.route('/clear/month', methods=['GET'])
@token_required
def clear(month):
    entries_collection.drop()
    return jsonify({"message": "Records cleared"}), 200

if __name__ == '__main__':
    app.run(debug=True)