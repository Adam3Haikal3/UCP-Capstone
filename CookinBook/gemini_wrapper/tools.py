import os
from django.conf import settings
import requests
import uuid
import json
from ucp_sdk.models.schemas.shopping import checkout_create_req
from ucp_sdk.models.schemas.shopping import checkout_update_req

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
        self.payment_handlers = []
            
    def discover_merchant(self):
        discovery_url = self.server_url + "/.well-known/ucp"

        # print(f"Discovery URL: {discovery_url}")

        r = requests.get(url=discovery_url)
        self.merchant_profile = r.json()

        if "dev.ucp.shopping" not in self.merchant_profile["ucp"]["services"]:
            raise ValueError("Merchant does not support dev.ucp.shopping")

        shopping_service = self.merchant_profile["ucp"]["services"]["dev.ucp.shopping"]

        # For MVP we are only focusing on REST
        self.get_rest(shopping_service)

        for c in self.merchant_profile["ucp"]["capabilities"]:
            self.capabilities.append(c["name"])

        self.payment_handlers = self.merchant_profile["payment"]["handlers"]

        # print(f"[UCP] Merchant Profile: {json.dumps(self.merchant_profile, indent=4)}")
        # print(f"[UCP] Rest Endpoint: {self.rest_endpoint}")
        # print(f"[UCP] Rest Schema: {json.dumps(self.rest_schema, indent=4)}")

    def get_rest(self, ss):
         if ss["rest"] is None:
             raise ValueError("Merchant does not support REST")

         schema_url = ss["rest"]["schema"]

         # Mock server has incorrect example schema url
         if os.getenv("UCP_MOCK_MODE"):
             schema_url = schema_url[:15] + "/2026-01-23" + schema_url[15:]
             
         # print(f"Schema URL: {schema_url}")
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
             if "id" in i:
                 d = {
                 "item": {
                     "id": i["id"],
                     "title": i["name"],
                 },
                 "quantity": 1, # Need to figure out how to normalize measures, so for now set to 1 instead of i["measure"]
             }
             else:
                 d = {
                 "item": {
                     "id": i["name"].lower(),
                     "title": i["name"],
                 },
                 "quantity": 1, # Need to figure out how to normalize measures, so for now set to 1 instead of i["measure"]
             }
             
             line_items.append(d)

         payload = {
             "buyer": {
                "name": "John Doe",
                "email": "john.doe@example.com",
             },
             "line_items": line_items,
             "currency": "USD",
             "payment": { 
                 "instruments": [],
                 "selected_instruments_id": None,
                 "handlers": self.payment_handlers
             },
             #"fulfillment": {
                 #"methods": [
                     #{
                        # "type": "shipping",
                        # "selected_destination_id": "addr_1",
                        # "groups": [
                        #     {
                        #         "selected_option_id": "exp-ship-us"
                        #     }
                        # ]
                         
                     #}
                 #]
             #}
         }
             
         response = requests.request(info["method"], url, headers=headers, json=payload)
         data = response.json()

         print(f"[UCP] Response: {json.dumps(data, indent=4)}")

         self.shopping_cart_id = data["id"]

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
    def set_fulfillment_method(self, method: str, address: dict = None):

        # Sets fulfillment method on current checkout. method: "shipping" or "pickup". Address: required if method is "shipping"

        if not self.shopping_cart_id:
            raise ValueError("Must call create_cart() before setting fulfillment method")
        
        if method == "shipping" and address is None:
            raise ValueError("Address is required for shipping fulfillment")
        
        # Operation is called "update_checkout" in the mock server schema. Verify against actual schema operationId when running mock server
        info = self.get_path("update_checkout")

        if info is None:
            raise ValueError("Merchant does not support update_checkout operation")
        
        # id is a path parameter in the URL (e.g. /checkout-session/{id})
        url = self.rest_endpoint + info["path"].replace("{checkout_id}", self.shopping_cart_id)

        # TODO Every time you call update_checkout you need to rebuild the entire payload.
        # Might be a good idea to just save the orignal payload as a class variable in the create_checkout method to re-use 
        # Since we will never update the line-items. I will let you decide

        # ASSUMPTION: fulfillment method is set via a "fulfillment" key in the payload with "method_type" as the field name — verify against actual mock server schema
        payload = {
            "fulfillment": {
                "method_type": method,
            }
        }

        if method == "shipping" and address:
            payload["fulfillment"]["destination"] = address
        
        response = requests.request(info["method"], url, headers=self.get_headers(), json=payload)

        print(f"[UCP] Set fulfillment response: {json.dumps(response.json(), indent=4)}")

        return response.json()

    def complete_purchase(self,):
        # Finalized order after cart creation and fulfillment method has been set. Call after create_cart() and set_fulfillment_method()

        if not self.shopping_cart_id:
            raise ValueError("Must call create_cart() before completing purchase")
        
        # Operation is called "complete_checkout" in the mock server schema.
        info = self.get_path("complete_checkout")

        if info is None:
            raise ValueError("Merchant does not support complete_checkout operation")

        # id is a path parameter (e.g. - /checkouts/{id}/complete).
        url = self.rest_endpoint + info["path"].replace("{id}", self.shopping_cart_id)

        # Placeholder payload that includes payment information, would need to change for an actual working bot
        payload = {
             "payment_data": { 
                 "id": "instr_agent_card",
                 "handler_id": "mock_payment_handler",
                 "handler_id": "mock_payment_handler",
                 "type": "card",
                 "brand": "Visa",
                 "last_digits": "4242",
                 "credential": {
                     "type": "token",
                     "token": "success_token"
                 },
                 "billing_address": {
                     "street_address": "123 Main St",
                     "address_locality": "Anytown",
                     "address_region": "CA",
                     "address_country": "US",
                     "postal_code": "12345",
                 }
             },
             "risk_signals": {
                 "ip": "127.0.0.1",
                 "broswer": "ucp-agent-tools",
             }
         }
        
        # ASSUMPTION: no additional payload needed to complete — just the checkout ID in the path. Real UCP implementations may require payment confirmation or other fields here
        response = requests.request(info["method"], url, headers=self.get_headers(), json=payload)

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
                  # Some paths have "parameters" which need to be skipped or else code breaks
                  if http_method == "parameters":
                      continue
                  
                  info = method[http_method]

                  if info["operationId"] == operation_name:
                      return {
                          'path': p,
                          'method': http_method.upper()
                      }
         return None
    
    def search_inventory(self, items: list[dict[str, str]]):
        # print(f"[UCP]: Original List of Ingredients: {items}")

        if os.getenv("UCP_MOCK_MODE"):
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_path = os.path.join(base_dir, 'data', 'mock_inventory.json')

                f = open(file_path, "r")
                f = json.load(f)
            except Exception as e:
                print(f"Error loading mock inventory: {e}")
                return items
            
            updated_items = [
                item
                for item in items
                if f.get(item["name"].lower()) is not None
            ]

            # print(f"[UCP] Updated List of Available Ingredients: {updated_items}")

            return updated_items
        
        # UCP search (The mock server we are using doesn't support this)
        # For right now this is just searching the catalog and picking the first match that comes back
        # This would definitly need to change if this was a full fledged product
        if "dev.ucp.shopping.catalog.search" not in self.capabilities:
             raise ValueError("Merchant is missing catalog search capability")
        
        info = self.get_path("search_catalog")

        url = self.rest_endpoint + info["path"]
        headers = self.get_headers()

        updated_items = []

        for i in items:
            payload = {
                "query": i["name"]
            }

            try:
                response = requests.request(info["method"], url, headers=headers, json=payload)

                data = response.json()
                products = data.get("products")

                if not products:
                    continue

                product = products[0]

                new_item = {
                    "name": product["title"],
                    "measure": i["measure"],
                    "id": product["id"],
                }

                updated_items.append(new_item)

            except Exception as e:
                print(f"[UCP] Failed to lookup {i["name"]}: {e}")

        return updated_items
    
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
