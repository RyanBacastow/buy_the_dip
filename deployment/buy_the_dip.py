#!/usr/bin/env python
# coding: utf-8

import yfinance as yf
import boto3
from os import environ as env


def calc_stock(high, current):
    return (current - high)/high


def convert_tuple(tup): 
    string_tup =  "{} : {}".format(tup[0], str(tup[1]))
    return string_tup


def create_message(pairs):
    message = "Ordered Portfolio:\n"
    for pair in pairs:
        message += convert_tuple(pair) + "\n"
    return message
    
    
def publish_message_sns(message):
    sns_arn = env.get('SNS_ARN').strip()
    sns_client = boto3.client('sns')
    try:
        print(message)

        response = sns_client.publish(
            TopicArn=sns_arn,
            Message=message
        )

        print(response)

    except Exception as e:
        print("ERROR PUBLISHING MESSAGE TO SNS: {}".format(e))


def read_tickers(file='stock_tickers.txt', period='5y'):
      
    pairs = dict()

    with open(file, 'r') as f:
        while True:
            # Get next line from file 
            ticker = (f.readline()).strip()

            if ticker == "":
                break
            else:
                print(ticker)

            stock = yf.Ticker(ticker)
            data = stock.history(env.get('PERIOD', period))
            
            close = data.Close[-1]
            high = max(data.Close)
            
            delta = calc_stock(high, close)
 
            pairs[ticker] = delta

            if not ticker:
                break
        
    return(sorted(pairs.items(), key=lambda x: x[1]))


def handler(event, context):
    """
    This function drives the AWS lambda. Requires 1 env var to work correctly: SNS_TOPIC which represents the topic arn to which
    you want to publish. 
    """
    pairs = read_tickers()
    message = create_message(pairs)
    print(message)
    #AWS LIVE VERSION ONLY:
    publish_message_sns(message)

