import os
import json
import requests
from typing import List
from datetime import datetime, timedelta, timezone
import logging

JST = timezone(timedelta(hours=+9), 'JST')

handler = logging.StreamHandler()
handler.setLevel(os.getenv("LOG_LEVEL", default=logging.DEBUG))
default_logger: logging.Logger = logging.getLogger(__name__)
default_logger.setLevel(os.getenv("LOG_LEVEL", default=logging.DEBUG))
default_logger.addHandler(handler)
default_logger.propagate = False

API_KEY_ID = os.environ.get('API_KEY_ID', default='keyId-gijAumTnOgFcNsiijZVbuTrldkicasCW')
AUTH_KEY = os.environ.get('AUTH_KEY', default='secret-LA7aR7KB03JXrM3CwCUSSBEckXS6nepOHGVxqSbHnY8vvdGjbHRQoHUwn1yyHFom')

AUTH_URL = 'https://api.soracom.io/v1/auth'
QUERY_SIMS_URL = 'https://api.soracom.io/v1/query/sims'
LIST_PORT_MAPPINGS = 'https://api.soracom.io/v1/port_mappings/subscribers/{imsi}'
ADD_PORT_MAPPINGS = 'https://api.soracom.io/v1/port_mappings'

class SoracomApi:

    def __init__(self, api_key_id, auth_key):

        self._api_key_id = api_key_id
        self._auth_key = auth_key

        self._api_key = None
        self._operator_id = None
        self._user_name = None
        self._token = None

        self._get_auth()

    def _get_auth(self,):
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            'authKeyId': self._api_key_id,
            'authKey': self._auth_key,
        }
        response = requests.post(url=AUTH_URL, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        auth_json = response.json()

        self._api_key = auth_json['apiKey']
        self._operator_id = auth_json['operatorId']
        self._user_name = auth_json['userName']
        self._token = auth_json['token']

    def list_sims(self, name):
        headers = {
            'accept': 'application/json;charset=UTF-8',
            'X-Soracom-API-Key': self._api_key,
            'X-Soracom-Token': self._token,
        }
        params = {}
        params['name'] = name
        params['limit'] = '10'
        params['session_status'] = 'NA'
        params['search_type'] = 'or'

        response = requests.get(url=QUERY_SIMS_URL, headers=headers, params=params)
        response.raise_for_status()
        sims_json = response.json()

        return sims_json

    def list_port_mappings(self, sim):
        """
        ポートマッピング一覧
        :param sim:
        :return:
        """
        headers = {
            'accept': 'application/json;charset=UTF-8',
            'X-Soracom-API-Key': self._api_key,
            'X-Soracom-Token': self._token,
        }
        sim_id = sim['simId']
        imsi = sim['profiles'][sim_id]['primaryImsi']
        response = requests.get(url=LIST_PORT_MAPPINGS.format(imsi=imsi), headers=headers,)
        response.raise_for_status()
        port_mappings = response.json()
        return port_mappings

    def add_port_mapping(self, sim, ip, port, duration):
        sim_id = sim['simId']
        imsi = sim['profiles'][sim_id]['primaryImsi']

        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json;charset=UTF-8',
            'X-Soracom-API-Key': self._api_key,
            'X-Soracom-Token': self._token,
        }

        params = {
            'destination': {
                'imsi': imsi,
                'port': port,
            },
            'duration': duration,
            'source': {
                'ipRanges': [
                    ip + '/32',
                ]
            },
            'tlsRequired': 'false',
        }
        response = requests.post(url=ADD_PORT_MAPPINGS, headers=headers, data=json.dumps(params))
        response.raise_for_status()
        port_mapping_json = response.json()
        print(json.dumps(port_mapping_json, indent=2))
        """
        curl -v -X POST "https://api.soracom.io/v1/port_mappings" \
            -H  "accept:application/json;charset=UTF-8" \
            -H  "X-Soracom-API-Key: ${API_KEY}" \
            -H  "X-Soracom-Token: ${TOKEN}" \
            -H  "Content-Type: application/json" \
            -d @portmapping.json > map_result.json
        """

def lambda_handler(event, context):

    default_logger.info(event)
    """
    {
        'body-json': {}, 
        'params': {
            'path': {}, 
            'querystring': {
                'url': 'https://youtu.be/Nzs4I52BRWc'
            }, 
            'header': {}
        }, 
        'stage-variables': {}, 
        'context': {
            'account-id': '401141590450', 
            'api-id': 'wnysfk91m1', 
            'api-key': 'test-invoke-api-key', 
            'authorizer-principal-id': '', 
            'caller': '401141590450', 
            'cognito-authentication-provider': '', 
            'cognito-authentication-type': '', 
            'cognito-identity-id': '', 
            'cognito-identity-pool-id': '', 
            'http-method': 'GET', 
            'stage': 'test-invoke-stage', 
            'source-ip': 'test-invoke-source-ip', 
            'user': '401141590450', 
            'user-agent': 'aws-internal/3 aws-sdk-java/1.11.984 Linux/5.4.102-52.177.amzn2int.x86_64 OpenJDK_64-Bit_Server_VM/25.282-b08 java/1.8.0_282 vendor/Oracle_Corporation cfg/retry-mode/legacy', 
            'user-arn': 'arn:aws:iam::401141590450:root', 
            'request-id': 'c2c800db-5183-4622-ad77-eec948bb6e2f', 
            'resource-id': 'xnx8jeazy2', 
            'resource-path': '/'
        }
    }
    """
    if 'url' in event['params']['querystring']:
        url = event['params']['querystring']['url']
        # response = job_exec_request(url, logger=default_logger)
        response = ()
        return {
            'statusCode': 200,
            'body': response
        }
    else:
        pass
        # return response_html


if __name__ == '__main__':
    api = SoracomApi(API_KEY_ID, AUTH_KEY)
    sims_json = api.list_sims(['SORACOM-001',])
    port_mappings = api.list_port_mappings(sims_json[0])
    for port_mapping in port_mappings:
        # print(json.dumps(port_mapping, indent=2))
        expired_time = port_mapping['expiredTime']
        expired_time = datetime.fromtimestamp(expired_time/1000.0).astimezone(JST)
        expired_time = expired_time.strftime("%Y/%m/%d %H:%M:%S")
        hostname = port_mapping['hostname']
        ip_address = port_mapping['ipAddress']
        port = port_mapping['port']
        dst_port = port_mapping['destination']['port']
        ip_ranges = port_mapping['source']['ipRanges'][0]
        print(f'{ip_address}:{port} -> {dst_port} from:{ip_ranges} until:{expired_time}')

    sanyo_ip = '220.220.107.158'

    api.add_port_mapping(sims_json[0], ip=sanyo_ip, port=80, duration=30*60)





    pass
