import os
import datetime

# os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8081"
import firebase_admin
from firebase_admin import credentials, firestore


class FBDatabase:
    db = None

    def __init__(self):
        if self.db is None:
            cred = credentials.Certificate(
                "../../keys/key.json"
                if os.path.isfile("../../keys/key.json")
                else "./keys/key.json"
            )
            default_app = firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print("initialized firestore client")

    def create_order(self, uid: str, order_items: dict):
        self.db.collection("pending_orders").document(uid).set(
            {"details": firestore.ArrayUnion(order_items)}
        )

    def get_order_cost(self, uid: str):
        user_orders = self.db.collection("pending_orders").document(uid).get()
        total_cost = 0
        for order in user_orders.get("details"):
            #  Use `product_id` to retrieve product price from `products`
            snap = self.db.collection("products").document(order["product_id"]).get()
            total_cost += snap.get("price") * order["count"]
        return total_cost

    def complete_order(self, uid, data):
        user_orders = (
            self.db.collection("pending_orders").document(uid).get().get("details")
        )
        self.db.collection("completed_orders").document(uid).collection(
            "order_history"
        ).document().set(
            {
                "datetime": datetime.datetime.now(),
                "order": firestore.ArrayUnion(user_orders),
                "extra": data
            }
        )
        # Remove from pending orders
        self.remove_pending_order(uid)

        # Remove from initiate transaction
        self.remove_initiate_transaction(uid)

    def get_orders(self, uid):
        order_objects = (
            self.db.collection("completed_orders")
            .document(uid)
            .collection("order_history")
            .get()
        )
        response = []
        for order_obj in order_objects:
            temp = order_obj.to_dict()
            temp["datetime"] = temp["datetime"].strftime("%Y-%m-%d %H:%M:%S")
            response.append(temp)

        return response

    def remove_pending_order(self, uid):
        if self.db.collection("pending_orders").document(uid).get().exists == True:
            self.db.collection("pending_orders").document(uid).delete()
            print("pending order deleted")
            return True

    def initiate_transaction(self, uid, data):
        if (
            self.db.collection("initiated_transactions").document(uid).get().exists
            == False
        ):
            self.db.collection("initiated_transactions").document(uid).set(data)

    def remove_initiate_transaction(self, uid):
        if (
            self.db.collection("initiated_transactions").document(uid).get().exists
            == True
        ):
            self.db.collection("initiated_transactions").document(uid).delete()
            print("initialized transaction deleted")
            return True

    def _fill_db(self, uid):

        self.db.collection("products").document("prd1").set(
            {"name": "Shoes", "price": 10.15,}
        )

        self.db.collection("products").document("prd2").set(
            {"name": "Pants", "price": 20,}
        )

        # self.db.collection("pending_orders").document(uid).set(
        #     {
        #         "details": firestore.ArrayUnion(
        #             [
        #                 {"product_id": "prd1", "count": 2},
        #                 {"product_id": "prd2", "count": 4},
        #             ]
        #         )
        #     }
        # )
    
    def is_order_complete(self, uid, ii):
        return len(self.db.collection("completed_orders").document(uid).collection("order_history").where("extra.USER1", "==", ii).get()) == 1


database = FBDatabase()
if 0:
    print(database.is_order_complete("user1", "9116dfff-373b-45be-a53d-735f8f3eff76"))
    # database._fill_db("user1")
    # database.complete_order("user1")

# database.get_orders("user1")
# database.remove_initiate_transaction("user1")
# database.initiate_transaction("user1","")
