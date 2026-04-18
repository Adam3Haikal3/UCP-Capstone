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
<<<<<<< Updated upstream
=======
        self.payment_handlers = []
        self.checkout_payload = None
>>>>>>> Stashed changes
            
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

         # Save payload as class variable so it's available for set_fulfillment_method() to resuse
         self.checkout_payload = payload 
         response = requests.request(info["method"], url, headers=headers, json=payload)

         print(f"[UCP] Response: {json.dumps(response.json(), indent=4)}")

         # TODO Save checkout id to class and to database
    
    def get_fulfillment_methods(self):

        # Fulfillment methods are typically either -> 1) shipping and 2) pickup

        # Returns available fulfillment methods from merchant profile. Call after discover_merchant()

        if self.merchant_profile is None:
            raise ValueError("Must call discover_merchant() before getting fulfillment methods")
        
        fulfillment_methods = []

        # ASSUMPTION: fulfillment-related capabilities contain "fulfillment", "shipping", or "pickup" in their name. Verify against actual mock server capability names when running.
        for capability in self.merchant_profile["ucp"]["capabilities"]:
            if "fulfillment" in capability["name"] or "shipping" in capability["name"] or "pickup" in capability["name"]:
                fulfillment_methods.append(capability["name"])
        
        # ASSUMPTION: if no fulfillment capabilities found, default to shipping and pickup as these are the standard UCP fulfillment options. Remove fallback once actual capability names are confirmed from mock server.
        if not fulfillment_methods:

            # Default fallback - most ucp merchants should support at least shipping
            fulfillment_methods = ["shipping", "pickup"]
        
        return {"fulfillment_methods": fulfillment_methods}
    
<<<<<<< Updated upstream
    def set_fulfillment_method(self, method: str, address: dict = None):
=======
    # Need to call update checkout three seperate times
    # The first time add this to the payload:
    """
    "fulfillment": {
                 "methods": [
                     {
                         "type": "shipping",
                     }
                 ]
             }
    """
    # Then in the response the server will send back a list of available destinations in the fulfillment -> methods section that
    # Looks like this:
    """
    "destinations": [
                    {
                        "extended_address": null,
                        "street_address": "123 Main St",
                        "address_locality": null,
                        "address_region": null,
                        "address_country": "US",
                        "postal_code": "62704",
                        "first_name": null,
                        "last_name": null,
                        "full_name": null,
                        "phone_number": null,
                        "id": "addr_1",
                        "city": "Springfield",
                        "region": "IL"
                    },
                    {
                        "extended_address": null,
                        "street_address": "456 Oak Ave",
                        "address_locality": null,
                        "address_region": null,
                        "address_country": "US",
                        "postal_code": "10012",
                        "first_name": null,
                        "last_name": null,
                        "full_name": null,
                        "phone_number": null,
                        "id": "addr_2",
                        "city": "Metropolis",
                        "region": "NY"
                    }
                        "region": "NY"
                    }
                ],
    """
    # Decide to pick one (Available addresses are those only stored in merchant server, we can't have the bot put on in)
    # and send another update request with the fullfilment looking like this now:
    """
    "fulfillment": {
                 "methods": [
                     {
                         "type": "shipping",
                         "selected_destination_id": {Chosen Addres id}
                     }
                 ]
             }
    """
    # At this point the response will then give you payment and shipping options that look like this in the response:
    # Groups is located once again in the fulfilments -> methods section
    """
    "groups": [
                    {
                        "id": "group_afedad28-55f1-4564-b42c-6a9e30c7c9bc",
                        "line_item_ids": [
                            "a41ddc5f-c8cc-4783-bdb7-e989e2ace57a",
                            "efdea997-eb6b-4fc0-ba19-00cfdbc4ad20",
                            "66de98f3-6e1a-461f-a928-e9930c0898cd",
                            "337dc647-cb87-46f9-b5a9-2f1064b7aef3",
                            "c8074f38-ff3c-495d-9073-6073afe53558",
                            "20d831e0-5109-4c0e-9dff-17b17ec1d4a9",
                            "ff3e02c1-7771-43ce-a7e1-101fea9ab2e5",
                            "f278c726-4104-43cf-a371-a031f49bae12",
                            "21651256-7755-4b5f-87ae-b21c4493e4f4",
                            "a8e76426-f77d-47dc-807b-d40cd109ab40"
                        ],
                        "options": [
                            {
                                "id": "std-ship",
                                "title": "Standard Shipping (Free)",
                                "description": null,
                                "carrier": null,
                                "earliest_fulfillment_time": null,
                                "latest_fulfillment_time": null,
                                "totals": [
                                    {
                                        "type": "subtotal",
                                        "display_text": null,
                                        "amount": 0
                                    },
                                    {
                                        "type": "total",
                                        "display_text": null,
                                        "amount": 0
                                    }
                                ]
                            },
                            {
                                "id": "exp-ship-us",
                                "title": "Express Shipping (US)",
                                "description": null,
                                "carrier": null,
                                "earliest_fulfillment_time": null,
                                "latest_fulfillment_time": null,
                                "totals": [
                                    {
                                        "type": "subtotal",
                                        "display_text": null,
                                        "amount": 1500
                                    },
                                    {
                                        "type": "total",
                                        "display_text": null,
                                        "amount": 1500
                                    }
                                ]
                            }
                        ],
    """
    # Decide to pick one and send one last update with the fulfillment section looking like:
    """
    "fulfillment": {
                 "methods": [
                     {
                         "type": "shipping",
                         "selected_destination_id": {Chosen Addres id},
                         "selected_option_id": {Chosen shipping option id}
                     }
                 ]
             }
    """
    # Then all will be good!
    def set_fulfillment_method(self, method: str, destination_id:  str = None, shipping_option_id: str = None):
>>>>>>> Stashed changes

        '''
        Sets fulfillment method on current checkout via 3 separate update_checkout calls.

        Step 1: Call w/ just method (e.g. "shipping") -> returns available destinations
        Step 2: Call w/ method + destination_id -> returns available shipping options
        Step 3: Call w/ method + destination_id + shipping_option_id -> finalizes fulfillment
        '''
        
        if not self.shopping_cart_id:
            raise ValueError("Must call create_cart() before setting fulfillment method")
        
<<<<<<< Updated upstream
        if method == "shipping" and address is None:
            raise ValueError("Address is required for shipping fulfillment")
        
        # ASSUMPTION: operation is called "update_checkout" in the mock server schema. Verify against actual schema operationId when running mock server
=======
>>>>>>> Stashed changes
        info = self.get_path("update_checkout")

        if info is None:
            raise ValueError("Merchant does not support update_checkout operation")
        
<<<<<<< Updated upstream
        # ASSUMPTION: checkout_id is a path parameter in the URL (e.g. /checkouts/{checkout_id}) — verify against actual schema paths
        url = self.rest_endpoint + info["path"].replace("{checkout_id}", self.shopping_cart_id)

        # ASSUMPTION: fulfillment method is set via a "fulfillment" key in the payload with "method_type" as the field name — verify against actual mock server schema
        payload = {
            "fulfillment": {
                "method_type": method,
            }
=======
        url = self.rest_endpoint + info["path"].replace("{checkout_id}", self.shopping_cart_id)

        # Rebuild full payload every time using stored checkout payload, as per UCP requirement: every update_checkout must include original fields
        payload = self.checkout_payload.copy()

        # Step 1: set method type, server returns available destinations
        fulfillment = {
            "methods": [
                {
                    "type": method,
                }
            ]
>>>>>>> Stashed changes
        }

        # Step 2: destination is now chosen, server will return shipping options
        if destination_id:
            fulfillment["methods"][0]["selected_destination_id"] = destination_id

        # Step 3: shipping option chosen, fulfillment is finalized
        if destination_id and shipping_option_id:
            fulfillment["methods"][0]["selected_option_id"] = shipping_option_id

        payload["fulfillment"] = fulfillment

        response = requests.request(info["method"], url, headers=self.get_headers(), json=payload)

        data = response.json()

        print(f"[UCP] Set fulfillment response: {json.dumps(data, indent=4)}")

<<<<<<< Updated upstream
    def complete_purchase(self):

=======
        return data
    def complete_purchase(self,):
>>>>>>> Stashed changes
        # Finalized order after cart creation and fulfillment method has been set. Call after create_cart() and set_fulfillment_method()

        if not self.shopping_cart_id:
            raise ValueError("Must call create_cart() before completing purchase")
        
        # ASSUMPTION: operation is called "complete_checkout" in the mock server schema. Verify against actual schema operationId when running mock server
        info = self.get_path("complete_checkout")

        if info is None:
            raise ValueError("Merchant does not support complete_checkout operation")

        # ASSUMPTION: checkout_id is a path parameter (e.g. - /checkouts/{checkout_id}/complete). May differ in actual mock server schema
        url = self.rest_endpoint + info["path"].replace("{checkout_id}", self.shopping_cart_id)
        
        # ASSUMPTION: no additional payload needed to complete — just the checkout ID in the path. Real UCP implementations may require payment confirmation or other fields here
        response = requests.request(info["method"], url, headers=self.get_headers(), json={})

        data = response.json()

        print(f"[UCP] Complete purchase response: {json.dumps(data, indent=4)}")

        if response.status_code == 200:
            return {
                "status": "success",
                "transaction_id": data.get("id", "UNKNOWN"),
                "message": "Order successfully placed via UCP.",
                "data": data,
            }
        else:
            return {
                "status": "failure",
                "message": data.get("error", "Unknown error from UCP server."),
                "data": data
            }

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
