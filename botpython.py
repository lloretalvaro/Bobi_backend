# -*- coding: UTF8 -*-
import requests
import datetime
import json
from ibm_watson import AssistantV1
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import pymongo
from decouple import config
import os


client = pymongo.MongoClient(config('MONGO_URI'))
mydb = client["BobiDB"]



def isInDB(nombre):
    mycol = mydb["Usuario"]
    query = {"nombre": nombre}
    mydoc = mycol.find_one(query)
    esta = False
    
    if mydoc == None:
        esta = False
    else:
        esta = True
    return esta

def InsertInDB(nombre):
    mycol = mydb["Usuario"]
    if nombre is not None and not isInDB(nombre):
        mydict = {"nombre" : nombre}
        mycol.insert_one(mydict)
def DeleteDB(nombre):
    mycol = mydb["Usuario"]
    if nombre is not None and isInDB(nombre):
        query = {"nombre" : nombre}
        mycol.delete_one(query)

def normalize(s):
    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("\n", ""),
        ('\"', ""),
    )
    for a, b in replacements:
        s = s.replace(a, b).replace(a.upper(), b.upper())
    return s

class BotHandler:
    def __init__(self, token):
            self.token = token
            self.api_url = "https://api.telegram.org/bot{}/".format(token)


    def get_updates(self, offset=0, timeout=30):
        method = 'getUpdates'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params)
        return resp

    def get_first_update(self):
        get_result = self.get_updates()

        if len(get_result) > 0:
            last_update = get_result[0]
        else:
            last_update = None

        return last_update


token = config('TOKEN_BOT') #Token of your bot
magnito_bot = BotHandler(token) #Your bot's name


def main():
    new_offset = 228565091
    print('hi, now launching...')
    authenticator = IAMAuthenticator(config('AUTHENTICATOR'))
    assistant = AssistantV2(
        version='2020-04-01',
        authenticator = authenticator
    )

    assistant.set_service_url(config('ASSISTANT_URL'))

    responseCreate = assistant.create_session(
        assistant_id=config('ASSISTANT_ID')
    ).get_result()

    
    while True:
        try: 
            all_updates=magnito_bot.get_updates(new_offset)

            if len(all_updates) > 0:
                for current_update in all_updates:
                    print(current_update)
                    first_update_id = current_update['update_id']
                    first_chat_id = current_update['message']['chat']['id']
                    if 'text' not in current_update['message']:
                        first_chat_text='New member'
                    else:
                        first_chat_text = current_update['message']['text']
                    if 'first_name' in current_update['message']:
                        first_chat_name = current_update['message']['chat']['first_name']
                    elif 'new_chat_member' in current_update['message']:
                        first_chat_name = current_update['message']['new_chat_member']['username']
                    elif 'from' in current_update['message']:
                        first_chat_name = current_update['message']['from']['first_name']
                    else:
                        first_chat_name = "unknown"

                        
                    if first_chat_text != '/start':  # do nothing
                        response = assistant.message(
                            assistant_id=config('ASSISTANT_ID'),
                            session_id=responseCreate['session_id'],
                            input={
                            'message_type': 'text',
                            'text': normalize(first_chat_text),
                            },
                            user_id=first_chat_id,
                        ).get_result()
                    
                        print(json.dumps(response, indent = 2))

                        intent = response['output']['intents'][0]['intent']
                        id_usuario = current_update['message']['chat']['id']

                        if intent == 'Subscripcion':
                            InsertInDB(id_usuario)    
                        elif intent == 'Desubscripcion':
                            DeleteDB(id_usuario) 
                        
                        
                        magnito_bot.send_message(first_chat_id, json.dumps(normalize(response['output']['generic'][0]['text']), indent=2))
                        new_offset = first_update_id + 1
                        
                    else:
                        magnito_bot.send_message(first_chat_id, 'Buenos días ' + first_chat_name + ', de aquí en adelante le resolveré todas las dudas que le surjan con respecto al inventario de la tienda, su horario y localización. Puede subscribirse escribiendo subscripción para recibir las nuevas remesas de productos que lleguen.')
                        new_offset = first_update_id + 1

                        

                        
        except Exception as e:
            print(e)
            magnito_bot.send_message(first_chat_id, 'Lo siento no le entendí, expreselo de otra manera por favor')
            new_offset = first_update_id + 1

               


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit()

