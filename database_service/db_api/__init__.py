from flask import Flask, g, request
from flask_restful import Resource, Api

from .database_endpoint import DatabaseEndpoint

# Create an instance of Flask
app = Flask(__name__)
app.secret_key = "hackme"
# Create the API
api = Api(app)

@app.route("/")
def index():
    return "", 200


api.add_resource(DatabaseEndpoint, "/cancel-order", endpoint="/cancel-order")
api.add_resource(DatabaseEndpoint, "/complete-order", endpoint="/complete-order")
api.add_resource(DatabaseEndpoint, "/order-cost", endpoint="/order-cost")
api.add_resource(DatabaseEndpoint, "/order-history", endpoint="/order-history")
api.add_resource(DatabaseEndpoint, "/create-order", endpoint="/create-order")
api.add_resource(DatabaseEndpoint, "/initiate-order", endpoint="/initiate-order")
api.add_resource(DatabaseEndpoint, "/cancel-initiate", endpoint="/cancel-initiate")
