import os

from typing import List
import logging

import azure.functions as func

from exporter import AzureExporter



def main(events: List[func.EventHubEvent]):

    device_id = os.environ.get('DATA_PROCESSOR_ID', default='sensor-event-handler')
    exporters = os.environ.get('DEVICE_EXPORTER', default='AZURE').split(',')
    topic_parsers = os.environ.get('TOPIC_PARSERS',
                                   default='devices/+/messages/events/?data_id=GPRMC:GPRMCParser,'
                                           'devices/+/messages/events/?data_id=GNRMC:GPRMCParser').split(',')
    for event in events:
        logging.info('Python EventHub trigger processed an event: %s',
                        event.get_body().decode('utf-8'))
