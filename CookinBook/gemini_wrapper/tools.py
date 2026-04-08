import os
from django.conf import settings
import requests
import uuid
import json

class UCPClientTools:
    def __init__(self):
        if os.getenv("UCP_MOCK_MODE"):
            self.server_url = settings.URL
        else: # TODO: Need to decide how a url will be picked outside of mock mode
            self.server_url = None
            
        self.merchant_profile = None
        self.rest_endpoint = None
        self.rest_schema = None
        self.capabilities = []
        self.shopping_cart_id = []
            
    def discover_merchant(self):
        discovery_url = self.server_url + "/.well-known/ucp"

        print(f"Discovery URL: {discovery_url}")

        r = requests.get(url=discovery_url)
        self.merchant_profile = r.json()

        if "dev.ucp.shopping" not in self.merchant_profile["ucp"]["services"]:
            raise ValueError("Merchant does not support dev.ucp.shopping")

        shopping_service = self.merchant_profile["ucp"]["services"]["dev.ucp.shopping"]

        # For MVP we are only focusing on REST
        self.get_rest(shopping_service)

        for c in self.merchant_profile["ucp"]["capabilities"]:
            self.capabilities.append(c["name"])
        # TODO Collect payment handlers

        print(f"[UCP] Merchant Profile: {json.dumps(self.merchant_profile, indent=4)}")
        print(f"[UCP] Rest Endpoint: {self.rest_endpoint}")
        print(f"[UCP] Rest Schema: {json.dumps(self.rest_schema, indent=4)}")

    def get_rest(self, ss):
         if ss["rest"] is None:
             raise ValueError("Merchant does not support REST")

         schema_url = ss["rest"]["schema"]

         # Mock server has incorrect example schema url
         if os.getenv("UCP_MOCK_MODE"):
             schema_url = schema_url[:15] + "/2026-01-23" + schema_url[15:]
             
         print(f"Schema URL: {schema_url}")
         self.rest_schema = requests.get(url=schema_url).json()

         self.rest_endpoint = ss["rest"]["endpoint"]
        
    def create_cart(self, items: list[dict[str, str]]):
         if "dev.ucp.shopping.checkout" not in self.capabilities:
             raise ValueError("Merchant is missing checkout capability")
         
         info = self.get_path("create_checkout")

         url = self.rest_endpoint + info["path"]

         headers = self.get_headers()

         line_items = []

         for i in items:
             d = {
                 "item": {
                     "id": i["name"].lower(),
                     "title": i["name"],
                 },
                 "quantity": i["measure"],
             }
             
             line_items.append(d)

         payload = {
             "line_items": line_items,
             "currency": "USD",
             "payment": { # TODO Need to collect the info for this from discovery profile
                 "instruments": [],
                 "selected_instruments_id": None,
                 "handlers": [
                     {
                         "id": "stripe",
                         "name": "Stripe",
                     }
                 ]
             },
         }
             
         response = requests.request(info["method"], url, headers=headers, json=payload)

         print(f"[UCP] Response: {json.dumps(response.json(), indent=4)}")

         # TODO Save checkout id to class and to database

    def get_path(self, operation_name):
         for p in self.rest_schema["paths"]:
              method = self.rest_schema["paths"][p]

              for http_method in method:
                  info = method[http_method]

                  if info["operationId"] == operation_name:
                      return {
                          'path': p,
                          'method': http_method.upper()
                      }
         return None
    
    def get_headers(self):
        headers = {
             "UCP-Agent": "https://agent.example/profile", # Example profile, technically need a real one for a full release
             "Request-Signature": "test", # In production this needs to be properly signed
             "Request-Id": str(uuid.uuid4()),
             "idempotency-key": str(uuid.uuid4()),
             "Content-Type": "application/json",
             "Accept": "application/json",
         }
        
        return headers
