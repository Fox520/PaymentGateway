import ballerina/crypto;
import ballerina/http;
import ballerina/java;
import ballerina/log;
import ballerina/stringutils;
import ballerina/time;

http:Client databaseEP = new ("http://localhost:6001");

http:Client paywebEP = new ("https://secure.paygate.co.za/payweb3");

string notify_url = "https://a59489fa1164.ngrok.io/notify";
string return_url = "https://a59489fa1164.ngrok.io/transaction-callback";

string PAYGATE_ID = "10011072130";
string PASSWORD = "secret";


const map<string> TRANSACTION_STATUS = {
    "0": "Not Done",
    "1": "Approved",
    "2": "Declined",
    "3": "Cancelled",
    "4": "User Cancelled",
    "5": "Received by PayGate",
    "7": "Settlement Voided"
};


@http:ServiceConfig {
    basePath: "/"
}
service sprinkle on new http:Listener(9090, {httpVersion: "2.0"}) {

    @http:ResourceConfig {
        methods: ["GET"],
        path: "/order-history/{uid}"
    }
    resource function orderHistory(http:Caller caller, http:Request request, string uid) returns @tainted error? {
        http:Response result = check databaseEP->get("/order-history?uid=" + <@untainted>uid);
        json converted = check result.getJsonPayload();
        check caller->respond(<@untainted>converted);
    }

    @http:ResourceConfig {
        methods: ["POST"],
        path: "/create-order"
    }
    resource function createOrder(http:Caller caller, http:Request request) returns @tainted error? {
        // Writes order items to db
        http:Response createOrderResponse = check databaseEP->post("/create-order", <@untainted>request);
        check caller->respond(check <@untainted>createOrderResponse.getTextPayload());
    }

    @http:ResourceConfig {
        methods: ["POST"],
        path: "/start-transaction"
    }
    resource function startTransaction(http:Caller caller, http:Request request) returns @tainted error? {
        // Convert payload to map
        json paramsRaw = check request.getJsonPayload();
        map<string> params = check map<string>.constructFrom(paramsRaw);

        // Writes order items to db
        http:Response orderCostResponse = check databaseEP->get("/order-cost?uid=" + <@untainted>params.get("uid"));

        string cost = check orderCostResponse.getTextPayload();

        string uid = <@untainted>params.get("uid");

        string datetime = check time:format(time:currentTime(), "yyyy-MM-dd HH:mm:ss");
        // Use on client to determine if order was completed or not
        handle uuid = createRandomUUID();
        // Initiate transaction on PayGate
        map<string> data = {
            "PAYGATE_ID": PAYGATE_ID,
            "REFERENCE": uid,
            "AMOUNT": "3299",            //cost,
            "CURRENCY": params.get("currency"),
            "RETURN_URL": return_url,
            "TRANSACTION_DATE": datetime,
            "LOCALE": params.get("locale"),
            "COUNTRY": params.get("country"),
            "EMAIL": params.get("email"),
            "PAY_METHOD": params.get("pay_method"),
            "NOTIFY_URL": notify_url,
            "USER1": uuid.toString()
        };

        data["CHECKSUM"] = generateChecksum(data);
        http:Request initiateRequest = new;
        initiateRequest.setTextPayload(<@untainted>mapToForm(data));
        check initiateRequest.setContentType("application/x-www-form-urlencoded");

        // Initiate transaction
        var x = paywebEP->post("/initiate.trans", initiateRequest);
        if (x is http:Response) {
            string resultRaw = check x.getTextPayload();
            // Note: checksum we receive is different from the one we generate.
            map<string> resultsFormatted = formToMap(resultRaw);
            log:printInfo(resultsFormatted.toString());
            if (resultsFormatted.hasKey("ERROR")) {
                _ = check caller->respond(resultsFormatted.get("ERROR"));
                return;
            }

            // Save transaction details to db

            _ = check databaseEP->post("/initiate-order", {
                    "uid": uid,
                    "data": resultsFormatted
                }
            );

            // Return html form with auto submit to redirect
            // https://docs.paygate.co.za/#redirect
            string msg = string `
        <html>
            <body onLoad="submitMyForm()">

                <form id="myForm" action="https://secure.paygate.co.za/payweb3/process.trans" method="POST" >
                    <input type="hidden" name="PAY_REQUEST_ID" value="${resultsFormatted.get("PAY_REQUEST_ID")}">
                    <input type="hidden" name="CHECKSUM" value="${resultsFormatted.get("CHECKSUM")}">
                </form>

            <script>
                function submitMyForm(){
                    document.getElementById("myForm").submit();
                }
            </script>
            </body>
        </html>
                        `;
            map<string> ss = {
                // On app resume, check if completed_orders/{uid}/order_history/{collections}/extra.USER1 == below
                "transaction_ref": uuid.toString(),
                "data": msg
            };
            http:Response clientResponse = new;
            clientResponse.setPayload(ss);
            clientResponse.setContentType("application/json");

            var res = caller->respond(clientResponse);

            if (res is error) {
                _ = check databaseEP->get("/cancel-initiate?uid=" + uid);
            }
        } else {
            panic x;
        }

        check caller->ok();

    }

    @http:ResourceConfig {
        methods: ["POST"],
        path: "/transaction-callback"
    }
    resource function transactionCallback(http:Caller caller, http:Request request) returns @tainted error? {
        map<string> data = formToMap(check request.getTextPayload());
        string transaction_status = TRANSACTION_STATUS.get(<@untainted>data.get("TRANSACTION_STATUS"));

        string msg = string `
        <html>
        <body>
            <h3>Transaction state: ${transaction_status}</h3>
            <h4>You may close this page to return to the app.<h4>
        <body>
        </html>
        `;

        http:Response clientResponse = new;
        clientResponse.setPayload(msg);
        clientResponse.setContentType("text/html");
        _ = check caller->respond(clientResponse);
    }

    @http:ResourceConfig {
        methods: ["POST"],
        path: "/notify"
    }
    resource function notifyCallback(http:Caller caller, http:Request request) returns @tainted error? {
        map<string> data = formToMap(check request.getTextPayload());
        if (data.get("TRANSACTION_STATUS") == "1" && data.get("RESULT_CODE") == "990017") {
            // Transaction is successful
            string uid = <@untainted>data.get("REFERENCE");
            _ = data.removeIfHasKey("REFERENCE");
            _ = data.removeIfHasKey("PAYGATE_ID");
            json dd = check json.constructFrom(data);
            map<json> reqData = {
                "uid": uid,
                "data": dd
            };
            http:Request req = new;
            req.setPayload(reqData);
            _ = check databaseEP->post("/complete-order", req);
        }
        _ = check caller->ok();
    }
}


function formToMap(string form) returns map<string> {
    map<string> returnMap = {};
    // a=1&b=2&c=3
    string[] splitResult = stringutils:split(form, "&");
    foreach string item in splitResult {
        string[] kv = stringutils:split(item, "=");
        returnMap[kv[0]] = kv[1];
    }
    return returnMap;
}

function mapToForm(map<string> data) returns string {
    string temp_string = "";

    foreach string item in data.keys() {
        temp_string += item + "=" + data.get(item) + "&";
    }
    return temp_string;
}

function generateChecksum(map<string> data) returns string {
    string temp_string = "";

    foreach string item in data.keys() {
        temp_string += data.get(item);
    }
    temp_string += PASSWORD;
    byte[] x = crypto:hashMd5(temp_string.toBytes());
    return x.toBase16();

}

function createRandomUUID() returns handle = @java:Method {
    name: "randomUUID",
    class: "java.util.UUID"
} external;
