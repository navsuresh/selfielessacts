from flask import Flask, request, send_from_directory, jsonify, make_response
from inspect import getsourcefile
import os
from os.path import abspath
import random
import pymongo
import time
import base64
from flask_restful import reqparse, abort, Api, Resource
import json
import re
import datetime
from datetime import datetime

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["database"]
act = db["acts"]
category = db["category"]
user = db["users"]

app = Flask(__name__)
api = Api(app)
PATH = abspath(getsourcefile(lambda: 0)).rsplit("/", 1)[0]


def validate_request(content, input_type, req_len):
    if isinstance(content, (input_type,)) == False:
        return False
    if len(content) != req_len:
        return False


def getNumberOfActs(categoryName):
    category = db.category.find_one(
        {"category.name": categoryName}
    )  # query for category
    if category == None:  # if category does not exist
        return -1
    print(category)
    number = category["category"]["count"]  # get size from the returned dictionary
    return number


# get Acts given category
def getActs(categoryName):
    acts = db.acts.find(
        {"act.category": categoryName}
    )  # query for acts given the category
    return acts


# Helper API for user login
@app.route("/api/v1/uservalidate", methods=["POST"])
def validate_user():
    body = request.get_json()
    print(type(body))
    query = db.users.find_one({"user.username": body["username"]})
    print(query)
    if query is None:
        return jsonify({}), 400
    if query["user"]["password"] != body["password"]:
        return jsonify({}), 400
    else:
        return jsonify({}), 201


# Helper API for generating unique act ID
@app.route("/api/v1/findactid", methods=["POST"])
def find_actid():
    cursor = db.acts.find().sort("act.actId", pymongo.ASCENDING)
    id = 0
    for i in cursor:
        print(i)
        if i["act"]["actId"] != str(id):
            break
        id += 1
    return jsonify([id]), 201


"""
APIs START HERE!!!!!!
"""

# API's 1-2
class User_normal(Resource):
    # Adding an user - API 1
    def post(self):
        try:
            content = request.json
        except:
            return make_response(jsonify({}), 400)

        if validate_request(content, dict, 2) == False:
            return make_response(jsonify({}), 400)

        for i in content.keys():
            if i not in ['username', 'password']:
                return make_response(jsonify({}), 400)
        
        if (not(isinstance(content["username"], str))):
            return make_response(jsonify({}), 400)
        
        if (not(isinstance(content["password"], str))):
            return make_response(jsonify({}), 400)

        # user already existing case
        query = user.find_one({"user.username": content["username"]})
        if query is not None:
            return make_response(jsonify({}), 400)

        regex = re.compile("^[a-fA-F0-9]{40}$")
        if not (regex.match(content["password"])):
            return make_response(jsonify({}), 400)

        dict_temp = {
            "user": {"username": content["username"], "password": content["password"]}
        }
        user.insert_one(dict_temp)
        return make_response(jsonify({}), 201)

    # New API - User List
    def get(self):
        x = user.find({})
        userlist = []
        for i in x:
            userlist.append(i["user"]["username"])
        if (len(userlist) == 0):
            return make_response('', 204)
        return make_response(jsonify(userlist), 200)

    def head(self):
        return make_response(jsonify({}), 405)


class User_delete(Resource):
    # Adding an user - API 2
    # Removing an user - API 2
    def delete(self, del_arg):
        query = user.delete_one({"user.username": del_arg})
        # user does not exist to be deleted
        if query.deleted_count == 0:
            return make_response(jsonify({}), 400)
        return make_response(jsonify({}), 200)

    def head(self, del_arg):
        return make_response(jsonify({}), 405)


api.add_resource(User_normal, "/api/v1/users")
api.add_resource(User_delete,"/api/v1/users/<del_arg>")

# API's 3-5
class Category_normal(Resource):

    # API - 3
    def get(self):
        # print("Inside here\n")
        x = category.find({})
        dict1 = {i["category"]["name"]: i["category"]["count"] for i in x}
        if len(dict1) == 0:
            return make_response('', 204)
        # response = app.response_class(
        #     response=json.dumps(y), mimetype='application/json')
        # return jsonify(dict1)
        return make_response(jsonify(dict1), 200)

    # API - 4
    def post(self):
        # print("Self",self)
        # print("Resource is ", str(Resource))
        # print("Self ifs", str(self))
        try:
            content = request.json
        except:
            return make_response(jsonify({}), 400)

        if validate_request(content, list, 1) == False:
            return make_response(jsonify({}), 400)
        
        if(not isinstance(content[0],str)):
            return make_response(jsonify({}), 400)

        temp = category.find_one({"category.name": content[0]})
        # print("Temp is",temp)
        # print("Temp is ", type((temp)))
        if temp is not None:
            return make_response(jsonify({}), 400)
        
        dict_temp = {"category": {"name": content[0], "count": 0}}
        # print(content)
        # print(type(content))
        category.insert(dict_temp)
        return make_response(jsonify({}), 201)

    def head(self):
        return make_response(jsonify({}), 405)


class Category_delete(Resource):

    # API - 5
    def delete(self, del_arg):
        temp = category.delete_one({"category.name": del_arg})
        if temp.deleted_count == 0:
            return make_response(jsonify({}), 400)

        #Deleting corresponding acts from act table    
        act.delete_many({"act.category": del_arg})
        # print(xyz)
        return make_response(jsonify({}), 200)

    def head(self, del_arg):
        return make_response(jsonify({}), 405)

api.add_resource(Category_normal, "/api/v1/categories")
api.add_resource(Category_delete, "/api/v1/categories/<del_arg>")


# API 6 and 8
@app.route("/api/v1/categories/<categoryName>/acts", methods = ["HEAD"])
def listActsHead(categoryName):
	return (
		jsonify({}),
		405
		)

@app.route("/api/v1/categories/<categoryName>/acts", methods=["GET"])
def listActs(categoryName):
    number = getNumberOfActs(categoryName)  # get number of acts of the given category

    if number == -1:
        return jsonify({}), 405  # method not allowed if category does not exist

    if number == 0:
        return '', 204  # no content if no acts under existing category

    startRange = request.args.get("start")  # get start parameter
    endRange = request.args.get("end")  # get end parameter

    if startRange == None and endRange == None:  # if API 6
        if number < 100:
            acts = getActs(categoryName)
            actsList = []
            for i in acts:
                print(i)
                i.pop("_id")  # remove the Mongo-DB's in-built ObjectId attribute
                i["act"].pop("category")
                i["act"]["actId"] = int(i["act"]["actId"])
                i["act"]["timestamp"] = i["act"]["timestamp"].strftime(
                    "%d-%m-%Y:%S-%M-%H"
                )
                # i["act"]["timestamp"][0] = i["act"]["timestamp"][0].strftime("%Y-%m-%d:%S:%M:%H") #convert timestamp to string for json conversion
                actsList.append(i['act'])
            response = json.dumps(actsList)
            return response, 200
        else:
            return (
                jsonify({}),
                413,
            )  # if number of acts in the given category is => 100 (Payload too large)

    else:  # if API 8

        if startRange == None or endRange == None:  #in case of a missing parameter
            return (
                jsonify({}),
                405,
            )

        if len(startRange) == 0 or len(endRange) == 0:
            return (
                jsonify({}),
                405,
            )

        print(endRange)
        startRange = int(startRange)
        endRange = int(endRange)

        if(startRange > endRange):
        	return jsonify({}), 405

        if endRange - startRange + 1 > 100:
            return jsonify({}), 413  # payload too large - range > 100

        if startRange < 1:  # if invalid range, method not allowed
            return jsonify({}), 405

        if endRange > number:
        	return jsonify({}), 413
        
        acts = getActs(categoryName).sort([[
            "act.timestamp", -1
            ],[
            "act.actId", -1
            ]]
        ) # sort in descending order of timestamp (latest first)

        tempList = []
        actsList = []
        for i in acts:  # since acts object is not indexable, create a tempList
            tempList.append(i)
        print(tempList)
        
        if startRange < 1:
            return jsonify({}), 405

        if endRange > len(tempList):
        	return jsonify({}), 413

        if(startRange == endRange):
            tempList[startRange - 1].pop("_id")
            tempList[i]["act"].pop("category")
            tempList[startRange - 1]["act"]["actId"] = int(tempList[startRange - 1]["act"]["actId"])
            tempList[startRange - 1]["act"]["timestamp"] = tempList[startRange - 1]["act"]["timestamp"].strftime(
                "%d-%m-%Y:%S-%M-%H"
            )
            actsList.append(tempList[startRange - 1])
        else:
            for i in range(startRange - 1, endRange):
                tempList[i].pop("_id")
                tempList[i]["act"].pop("category")
                tempList[i]["act"]["actId"] = int(tempList[i]["act"]["actId"])
                tempList[i]["act"]["timestamp"] = tempList[i]["act"]["timestamp"].strftime(
                    "%d-%m-%Y:%S-%M-%H"
                )
                actsList.append(tempList[i])
        
        newList = list()
        for i in actsList:
            newList.append(i['act'])
        response = json.dumps(newList)
        return response, 200


# API - 7

@app.route("/api/v1/categories/<categoryName>/acts/size", methods=["HEAD"])
def getNumberOfActsGivenCategoryHeadError(categoryName):
	return (
		jsonify({}),
		405
		)


@app.route("/api/v1/categories/<categoryName>/acts/size", methods=["GET"])
def getNumberOfActsGivenCategory(categoryName):
    number = getNumberOfActs(categoryName)

    if number == -1:
        return jsonify({}), 405
    elif number == 0:
        return '', 204
    
    return jsonify([number]), 200


# API - 9
@app.route("/api/v1/acts/upvote", methods=["POST"])
def upvote():
    body = request.get_json()
    if validate_request(body, list, 1) == False:
            return jsonify({}), 400
    if (not(isinstance(body[0], int))):
            return jsonify({}), 400
    query = db.acts.find_one({"act.actId": str(body[0])})
    if query is None:
        print("Act Does Not Exist!")
        return jsonify({}), 400
    #check if int
    db.acts.update_one({"act.actId": str(body[0])}, {"$inc": {"act.upvotes": 1}})
    return jsonify({}), 200


# API - 10
@app.route("/api/v1/acts/<actId>", methods=["DELETE"])
def removeAct(actId):
    body = request.get_json()
    if validate_request(body, dict, 0) == False:
            return jsonify({}), 400
    query = db.acts.find_one({"act.actId": actId})
    if query is None:
        print("Act Does Not Exist!")
        return jsonify({}), 400

    db.category.update_one(
        {"category.name": query["act"]["category"]}, {"$inc": {"category.count": -1}}
    )
    db.acts.delete_one({"act.actId": actId})
    return jsonify({}), 200


# API - 11
@app.route("/api/v1/acts", methods=["POST"])
def uploadAct():
    body = request.get_json()
    if validate_request(body, dict, 6) == False:
            return jsonify({}), 400
    validate_set = {"actId", "username", "timestamp", "caption", "categoryName", "imgB64"}
    if set(body.keys()) != validate_set:
        print("Invalid Format of Request!")
        return jsonify({}), 400
    if (not(isinstance(body["actId"], int))):
        print("actId must be int!")
        return jsonify({}), 400
    if (not(isinstance(body["username"], str))):
        return jsonify({}), 400
    if (not(isinstance(body["timestamp"], str))):
        return jsonify({}), 400
    if (not(isinstance(body["caption"], str))):
        return jsonify({}), 400
    if (not(isinstance(body["categoryName"], str))):
        return jsonify({}), 400
    if (not(isinstance(body["imgB64"], str))):
        return jsonify({}), 400
    
    query = db.acts.find_one({"act.actId": str(body["actId"])})
    if query is not None:
        print("ActID already Exists!")
        return jsonify({}), 400

    try:
        a = datetime.strptime(body["timestamp"], "%d-%m-%Y:%S-%M-%H")
    except:
        print("Timestamp format not correct!")
        return jsonify({}), 400
    
    print(body["username"])
    query = db.users.find_one({"user.username": body["username"]})
    if query is None:
        print("User does not exist!")
        return jsonify({}), 400

    try:
        base64.b64decode(body["imgB64"])
    except:
        print("Image not Base64 Encoded")
        return jsonify({}), 400
    
    if "upvotes" in body:
        print("No upvotes field is to be set!")
        return jsonify({}), 400
    
    query = db.category.find_one({"category.name": body["categoryName"]})
    if query is None:
        print("Category does not exist!")
        return jsonify({}), 400
    toInsert = {
        "act": {
            "actId": str(body["actId"]),
            "username": body["username"],
            "timestamp": a,
            "caption": body["caption"],
            "upvotes": 0,
            "imgB64": body["imgB64"],
            "category": body["categoryName"],
        }
    }
    
    db.acts.insert_one(toInsert)
    db.category.update_one(
        {"category.name": body["categoryName"]}, {"$inc": {"category.count": 1}}
    )
    return jsonify({}), 201



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)

