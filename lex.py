import dateutil.parser
import datetime
import time
import os
import logging
import sys
import elasticache_auto_discovery
from pymemcache.client.hash import HashClient
from check import finalImage

import pymysql
import sys

REGION = 'us-east-1'


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def sendtocache(link):
	elasticache_config_endpoint = "giftbot.h0k94j4.cfg.use1.cache.amazonaws.com:11211"
	nodes = elasticache_auto_discovery.discover(elasticache_config_endpoint)
	nodes = map(lambda x: (x[1], int(x[2])), nodes)
	memcache_client = HashClient(nodes)
	print nodes
	memcache_client.set('ImageLink', link[5])
	print link[5]
	memcache_client.set('ImageName', link[4])
	print link[4]



""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    print "Close"
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }
    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def validate_GiftBot(AfternoonTime, FavProduct, PersonalityFinder):
    AfternoonTimeData = ['go out to eat', 'play with the kids', 'work on my fitness', 'relax at home', 'go shopping']
    if AfternoonTime is not None and AfternoonTime.lower() not in AfternoonTimeData:
        return build_validation_result(False,
                                       'AfternoonTime',
                                       'We do not have gifts related to slot AfternoonTime {}, would you like a different type of activity?'.format(AfternoonTime))
	FavProductData = ['apparel','stationary','tech accessories','home goods','health and wellbeing items']
	if FavProduct is not None and FavProduct.lower() not in FavProductData:
	    return build_validation_result(False,
                                       'FavProduct',
                                       'We do not have gifts related to slot FavProduct {}, would you like a different type of Object?'.format(FavProduct))
	PersonalityFinderData = ['practical','organized','thoughtful','energetic','calm']
	if PersonalityFinder is not None and PersonalityFinder.lower() not in PersonalityFinderData:
	    return build_validation_result(False,
                                       'PersonalityFinder',
                                       'We do not have gifts related to slot PersonalityFinder {}, would you like a different type of Personality?'.format(PersonalityFinder))
    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """

def selectGift(AfternoonTime,FavProduct):
	print "This function fetches content from mysql RDS instance"
    result = []
    print "Trying to connect"
    conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
    print "connected"
	sql = "select * from gift_mapping where slot1='%s' and slot2='%s'"%(AfternoonTime,FavProduct)
    with conn.cursor() as cur:
		cur.execute(sql)
		cur.close()
        for row in cur:
            result.append(list(row))
        print result
    return(result)


def GiftBot(intent_request):
    AfternoonTime = get_slots(intent_request)["AfternoonTime"]
    FavProduct = get_slots(intent_request)["FavProduct"]
    PersonalityFinder = get_slots(intent_request)["PersonalityFinder"]
    source = intent_request['invocationSource']
    print source
    if source == 'DialogCodeHook':
        slots = get_slots(intent_request)
        validation_result = validate_GiftBot(AfternoonTime, FavProduct, PersonalityFinder)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
    if source == 'FulfillmentCodeHook':
	    print "GiftBot"
	    afternoon = {"go out to eat":'1a', "play with the kids":'2a', "work on my fitness":'3a', "relax at home":'4a', "go shopping":'5a'}
	    favourite = {"apparel":'1f', "stationery":'2f', "tech accessories":'3f', "home goods":'4f', "health and wellbeing items":'5f'}
	    personality = {"practical":'1p', "organized":'2p', "thoughtful":'3p', "energetic":'4p', "calm":'5p'}
	    imageDet = selectGift(afternoon[AfternoonTime.lower()], favourite[FavProduct.lower()], personality[PersonalityFinder.lower()])
	    sendtocache(imageDet[0])
    print "Going to Close"
    time.sleep(2)
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'We have found the perfect gift for You!!!! Please click on the below image to get your surprise!!!'})


""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """
    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))
    intent_name = intent_request['currentIntent']['name']
    # Dispatch to your bot's intent handlers
    if intent_name == 'GiftsRepository':
        return GiftBot(intent_request)
    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    print event
    return dispatch(event)
