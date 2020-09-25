import os
import json
import webbrowser
from kivy.network.urlrequest import UrlRequest
from kivy.storage.dictstore import DictStore

from kivy.app import App
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen

BASE_URL = "https://c73e12ff8ac1.ngrok.io"
USER_ID = "user1"

store = DictStore("tempo.dat")
Builder.load_string(
    """
<HomeScreen>:
    BoxLayout:
        orientation: "vertical"
        Button:
            text: "Create order"
            on_release: root.create_order()
        Button:
            text: "start transaction"
            on_release: root.start_transaction()
        Button:
            text: "check if transaction is complete"
            on_release: root.is_transaction_complete()
        Label:
            text: root.status

"""
)

# Declare both screens
class HomeScreen(Screen):
    status = StringProperty("meh")

    def create_order(self):
        my_order = {
            "uid": "user1",
            "products": [
                {"product_id": "prd1", "count": 3},
                {"product_id": "prd2", "count": 2},
            ],
        }
        headers = {'Content-type': 'application/json',
          'Accept': 'application/json'}
        UrlRequest(
            f"{BASE_URL}/create-order",
            req_body=json.dumps(my_order),
            req_headers=headers,
            on_success=self.on_order_success,
            on_error=self.on_order_error,
        )

    def on_order_success(self, *args):
        # (<UrlRequest(Thread-1, started daemon 7296)>, '{\n    "cost": "70.45"\n}\n')
        data = json.loads(args[1])
        self.status = str(data)
    
    def on_order_error(self, *args):
        self.status = str(args)
    
    def start_transaction(self):
        info = {
            "uid": "user1",
            "currency":"ZAR",
            "locale": "en-za",
            "country": "ZAF",
            "pay_method":"CC",
            "email": "customer@paygate.co.za"
        }
        headers = {'Content-type': 'application/json',
          'Accept': 'application/json'}
        UrlRequest(
            f"{BASE_URL}/start-transaction",
            req_body=json.dumps(info),
            req_headers=headers,
            on_success=self.on_start_transaction_success,
            on_error=self.on_start_transaction_error,
        )
    
    def on_start_transaction_success(self, *args):
        data = args[1]
        transaction_ref = data["transaction_ref"]
        store.put("transaction_ref", transaction_ref=transaction_ref)
        html_form = data["data"]
        f = open("temporary.html", "w")
        f.write(html_form)
        f.close()
        webbrowser.open(os.path.abspath("temporary.html"))
    
    def on_start_transaction_error(self, *args):
        self.status = str(args)
    
    def is_transaction_complete(self):
        order_id = store.get("transaction_ref")["transaction_ref"]
        print(order_id)
        UrlRequest(
            f"{BASE_URL}/is-order-complete/{USER_ID}/{order_id}",
            on_success=self.on_transaction_complete_success,
            on_error=self.on_transaction_complete_error,
        )
    
    def on_transaction_complete_success(self, *args):
        self.status = str(args)
    
    def on_transaction_complete_error(self, *args):
        self.status = str(args)


# Create the screen manager
sm = ScreenManager()
sm.add_widget(HomeScreen(name="menu"))


class MyShop(App):
    def build(self):
        return sm
    
    def on_resume(self):
        return True

if __name__ == "__main__":
    MyShop().run()
