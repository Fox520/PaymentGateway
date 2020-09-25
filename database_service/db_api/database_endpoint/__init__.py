import traceback
from datetime import datetime
# from flask import jsonify
from flask_restful import Resource, reqparse, request

from ..fb_database import database


class DatabaseEndpoint(Resource):
    def get(self, *args, **kwargs):
        try:
            print(request.path)
            uid = request.args["uid"]
            if "/cancel-order" in request.path:
                database.remove_pending_order(uid)
                database.remove_initiate_transaction(uid)
                return "ok"
            elif "/cancel-initiate" in request.path:
                database.remove_initiate_transaction(uid)
                return "ok"
            
            elif "/order-cost" in request.path:
                return str(database.get_order_cost(uid))
            elif "/order-history" in request.path:
                return database.get_orders(uid)
            elif "/is-order-complete" in request.path:
                return database.is_order_complete(uid, request.args["order-id"])

        except:
            print(traceback.format_exc())
            return "failed, check console log"

    def post(self, *args, **kwargs):
        params = request.get_json()
        if "/create-order" in request.path:
            database.create_order(params["uid"], params["products"])
            cost = database.get_order_cost(params["uid"])
            return {"cost":str(cost)}
        elif "/initiate-order" in request.path:
            database.initiate_transaction(params["uid"], params["data"])
            return "1"
        elif "/complete-order" in request.path:
            database.complete_order(params["uid"], params["data"])
            return "ok"

