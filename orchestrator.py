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

    # call oc-core (which in turn will call feature collectors)

    # call incentive-provider and data-provider (asynchronously?)


    response = app.response_class(
        response=f'{{"request_id": {request_id}}}',
        status=200,
        mimetype='application/json'
    )
    return response
    
    
if __name__ == '__main__':
    
    FLASK_PORT = 5000
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379

    os.environ["FLASK_ENV"] = "development"

    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    app.run(port=FLASK_PORT, debug=True)