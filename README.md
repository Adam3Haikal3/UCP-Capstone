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
Before starting, ensure that ElasticSearch is downloaded and that the server is running

Then, you need to index recipes into the ES server from TheMealDB. CD into CookinBook
1. type into the shell one-by-one:

    - python manage.py shell
    - from gemini_wrapper.es import seed_from_db
    - seed_from_db()

After a little wait, all the recipes should be indexed into the recipe index

Now, to run the recipe search, follow the instructions to run the CookinBook bot and ask for meals

