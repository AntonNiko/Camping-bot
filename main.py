#! /usr/bin/env python3
import boto3
from botocore.exceptions import ClientError
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep

# Logging config
LOG_FILENAME = 'app.log'
logging.basicConfig(filename=LOG_FILENAME, format='%(asctime)s %(message)s', level=logging.INFO)

# App config
DESIRED_CAMPGROUND = 'Ruckle Park'
DESIRED_SEARCH_DATE = '08/15/2021'

# Selenium config
CHROMEDRIVER_PATH = '/usr/bin/chromedriver'

options = Options()
options.headless = True
driver = webdriver.Chrome(CHROMEDRIVER_PATH, options=options)

# SES config
SENDER = 'ant.nikitenko@gmail.com'
RECIPIENT = 'ant.nikitenko@protonmail.com'
AWS_REGION = 'us-west-2'
SUBJECT = 'PARK NOTIFICATION: Available Spot'
CHARSET = 'UTF-8'
client = boto3.client('ses', region_name=AWS_REGION)


def send_email_notification(body):
    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': body,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': body,
                    }
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        logging.info(e.response['Error']['Message'])
    else:
        logging.info('Email sent! Message ID:'),
        logging.info(response['MessageId'])


def fetch_campground_availability():
    # Open webpage and search for park availability
    try:
        logging.info('Fetch home page...')
        driver.get('https://www.discovercamping.ca/bccweb/')

        logging.info('Fill in search parameters...')
        search_park_input = driver.find_element_by_id('txtSearchparkautocomplete')
        search_park_input.send_keys(DESIRED_CAMPGROUND)

        sleep(3)

        search_park_select = driver.find_element_by_class_name('Park-icon')
        search_park_select.click()

        arrival_date_input = driver.find_element_by_id('mainContent_txtArrivalDate')
        arrival_date_input.send_keys(DESIRED_SEARCH_DATE)

        stay_length_input = driver.find_element_by_id('ddlHomeNights')
        stay_length_input.send_keys('1')

        search_button = driver.find_element_by_xpath('//a[@title=\'Click on Search Button\']')
        search_button.click()

    except Exception as e:
        logging.error('Error fetching home page and executing search:')
        logging.error(e)
        logging.error('Exiting...')
        return

    # Select page to show availability at specific park
    try:
        sleep(1)
        logging.info('Selecting availability calendar...')
        check_availability_button = driver.find_elements_by_class_name('btnFacilityclick')
        check_availability_button[0].click()

    except Exception as e:
        logging.error('Error selecting the availability calendar for the site')
        logging.error(e)
        logging.error('Exiting...')
        return

    # Analyze each camping spot (unit) to determine if any has available spots
    sleep(5)

    logging.info('Analyzing units...')
    free_units = []
    units_all = driver.find_elements_by_class_name('unitdata')
    for unit in units_all:
        unit_column = unit.find_element_by_class_name('first_td_new')
        unit_text = unit_column.find_element_by_tag_name('a').get_attribute('title')
        if not re.match('^Standard #\d{1,2}$', unit_text):
            continue

        unit_row = unit_column.find_element_by_xpath('..')
        columns_contain_available = any([col.get_attribute('class') == 'blue_brd_box' for col in unit_row.find_elements_by_xpath('./*')])
        logging.info(unit_text + ': ' + str(columns_contain_available))

        if columns_contain_available:
            free_units.append(unit_text)

    # Send email notification if any units are available
    if len(free_units) > 0:
        send_email_notification("Available spot(s): " + "; ".join(free_units))


if __name__ == '__main__':
    while True:
        fetch_campground_availability()
        logging.info('==========\nPAUSING...\n==========')
        sleep(90)
