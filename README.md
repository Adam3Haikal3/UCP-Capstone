# Cookin' Book

## Install dependencies
pip install -r requirements.txt

## Install ElasticSearch
pip install elasticsearch-dsl django-elasticsearch-dsl

## How to run:
cd into CookinBook  
python manage.py runserver

## How to test the mock gemini wrapper:
cd into CookinBook
1. type into shell one-by-one:

    - python manage.py shell
    - from gemini_wrapper.client import CookinBookBot 
    - bot = CookinBookBot()

2. paste this whole loop in the shell (so you don't need to always type print(bot.send_message("..."))): 
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "quit":
            break
        response = bot.send_message(user_input)
        print("Bot:", response)
3. press enter twice, should see 'You:'

4. You can now start a conversation (ex. I want to make tacos)

to close the chat, type 'quit'
exit the shell, type 'exit()'

### How to run ElasticSearch Mock Recipe Search
Before starting, ensure that ElasticSearch is downloaded on your computer and that the server is running
Make sure to include the server password and CA cert fingerprint in the .env

Then, you need to first index recipes into the ES server from TheMealDB. 
CD into CookinBook
1. type into the shell one-by-one:

    - python manage.py shell
    - from gemini_wrapper.es import seed_from_mealdb
    - seed_from_mealdb()

After a small wait, all the recipes should be indexed into the recipe index

Now, to run the recipe search, follow the instructions under "how to test the mock gemini wrapper"

### How to run UCP with Mock Server
Follow this link to access the public UCP Mock Sever: https://github.com/Upsonic/ucp-client

Before going further, replace the "inventory" and "products" cvs files located in the server's test_data folder
with the "server_inventory" and "server_products" cvs files located in the data folder of this CookinBook project

Then, follow the README instructions of the UCP Mock Server to run before attempting to create a checkout cart with
the CookinBook bot