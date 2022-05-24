import os
import json
import redis
from flask import Flask, request
import configparser as cp
import requests
import logging
import aiohttp
import asyncio
import time

from r2r_offer_utils.cache_operations import read_data_from_cache_wrapper, store_simple_data_to_cache_wrapper
from r2r_offer_utils.logging import setup_logger

service_name = os.path.splitext(os.path.basename(__file__))[0]
app = Flask(service_name)

# config
config = cp.ConfigParser()
config.read(f'{service_name}.conf')

# cache
cache = redis.Redis(host=config.get('cache', 'host'),
                    port=config.get('cache', 'port'),
                    decode_responses=True)

TIMEOUT = float(config.get('running', 'timeout'))

# init logging
logger, ch = setup_logger()
logger.setLevel(logging.INFO)

async def call_service(session, url):
    
    logger.info(f'o-o-o-o-o-o-o-o Sending request: {url}... o-o-o-o-o-o-o-o')
    try:
        async with session.get(url) as response:
            json_response = await response.json(content_type=None)
            logger.info(f'o-o-o-o-o-o-o-o Received response from {url}. o-o-o-o-o-o-o-o')
            return json_response
    except asyncio.CancelledError:
        logger.info(f'O-o-O-o-O-o-O A timeout occurred in {url}. O-o-O-o-O-o-O')
        response = app.response_class(status=504,
                                      mimetype='application/json')
        return response
    except Exception as exc:
        logger.info(f'X-X-X-X-X-X Something went wrong in {url}. X-X-X-X-X-X')
        logger.info(exc)
        response = app.response_class(status=500,
                                      mimetype='application/json')
        return response


async def send_async_requests(request_id):
    
    logger.info('Handling asynchronous requests to oc-core, data-provider and incentive-provider.')
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        tasks.append(asyncio.ensure_future(call_service(session, f'http://oc-core:5000/{request_id}')))
        tasks.append(asyncio.ensure_future(call_service(session, f'http://data-provider:5000/?request_id={request_id}')))
        tasks.append(asyncio.ensure_future(call_service(session, f'http://incentive-provider:5000/?request_id={request_id}')))
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=TIMEOUT)
            logger.info('Asynchronous requests have been handled.')
            #return (oc_core_response, data_provider_response, incentive_provider_response)
            
        except asyncio.TimeoutError:
            #for t in tasks:
            #    t.cancel()
            logger.info(f'O-o-O-o-O-o-O Timeout (after {TIMEOUT} seconds) O-o-O-o-O-o-O')
        
        oc_core_response = tasks[0].result() if tasks[0].done() else {}
        data_provider_response = tasks[1].result() if tasks[1].done() else {}
        incentive_provider_response = tasks[2].result() if tasks[2].done() else {}
        return (oc_core_response, data_provider_response, incentive_provider_response)


@app.route('/train', methods=['GET'])
def train_classifier():
    logger.info('Sending GET request to thor-wrapper')
    thor_response = requests.get(url='http://thor-wrapper:5000/train')
    logger.info(f'Response from thor-wrapper: {thor_response}')
    response = app.response_class(
        status=200,
        mimetype='application/json'
    )
    return response

    
@app.route('/compute', methods=['POST'])
def handle_request():
    
    # receive the TRIAS request data
    request.get_data()
    trias_data = request.data
    
    # send the TRIAS to the trias-extractor
    logger.info('Sending POST request to trias-extractor...')
    trias_extractor_response = requests.post(url='http://trias-extractor:5000/extract',
                                             data=trias_data,
                                             headers={'Content-Type': 'application/xml'}).json()
    logger.info('Received response from trias-extractor.')
    request_id = str(trias_extractor_response['request_id'])

    logger.info('Sending POST request to geolocation-fc...')
    geolocation_fc_response = requests.post(url='http://geolocation-fc:5000/compute',
                                            json={"request_id": request_id, "geo_attributes": ["start_point", "end_point", "via_locations"]},
                                            headers={'Content-Type': 'application/json'})
    logger.info(f'Response from geolocation-fc:{geolocation_fc_response}')

    # send asynchronous requests to oc-core, incentive-provider and data-provider
    (oc_core_response, 
    data_provider_response, 
    incentive_provider_response) = asyncio.run(send_async_requests(request_id))

    logger.info(f'Response from oc-core: {oc_core_response}')
    logger.info(f'Response from data-provider: {data_provider_response}')
    logger.info(f'Response from incentive-provider: {incentive_provider_response}')


    logger.info('Sending POST request to thor-wrapper...')
    thor_response = requests.post(url='http://thor-wrapper:5000/rank',
                                            json={"request_id": request_id},
                                            headers={'Content-Type': 'application/json'})
    logger.info(f'Response from thor-wrapper:{thor_response}')

    if thor_response.status_code == 200:
        offer_scores = thor_response.json()['offers']
        logger.info(offer_scores)
    elif oc_core_response != {}:
        # back-up method in case of THOR failure
        offer_scores = {}
        for offer_id in oc_core_response:
            offer_scores[offer_id] = sum(oc_core_response[offer_id].values())
        offer_scores = {offer_id: offer_scores[offer_id] / max(offer_scores.values()) for offer_id in offer_scores}
    else:
        return app.response_class(status=500,
                                  mimetype='application/json')

    ranks = {}
    ranks = {offer_id: i for (i, offer_id) in enumerate(sorted(offer_scores, key=offer_scores.get, reverse=True))}

    # composition of the final response
    final_result = {'result' : []}

    if oc_core_response != {}:
        offer_ids = oc_core_response.keys()
    elif incentive_provider_response != {}:
        offer_ids = incentive_provider_response.keys()
    elif thor_response.status_code == 200:
        offer_ids = offer_scores.keys()
    else:
        return app.response_class(status=500,
                                  mimetype='application/json')

    for offer_id in offer_ids:
        offer_data = {}
        offer_data['offer_id'] = offer_id

        if oc_core_response != {}:
            offer_data['categories'] = oc_core_response[offer_id]
        else:
            offer_data['categories'] = {}

        if incentive_provider_response != {}:
            offer_data['blockchain-incentives'] = incentive_provider_response['offers'][offer_id]
        else:
            offer_data['blockchain-incentives'] = {}
        
        if ranks and offer_scores:
            offer_data['ranking'] = {'rank':ranks[offer_id], 'score': offer_scores[offer_id]}
        else:
            offer_data['ranking'] = {}

        final_result['result'].append(offer_data)
    
    response = app.response_class(
            response=final_result,
            status=200,
            mimetype='application/json'
        )
    return final_result
    
    
if __name__ == '__main__':
    
    FLASK_PORT = 5000
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379

    os.environ["FLASK_ENV"] = "development"

    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    app.run(port=FLASK_PORT, debug=True)