#!/usr/bin/env python
# coding: utf-8

import yfinance as yf
import boto
from os import environ as env


def calc_stock(high, current):
    ratio = (current - high) / high
    return ratio


def convert_tuple(tup):
    string_tup = "{} : {}".format(tup[0], str(tup[1]))
    return string_tup


def create_message(pairs):
    message = "\nORDERED RATIOS:\n\n"
    for pair in pairs:
        message += convert_tuple(pair) + "\n"
    return message


def publish_message_sns(message):
    sns_arn = env.get('SNS_ARN').strip()
    sns_client = boto3.client('sns')
    try:
        response = sns_client.publish(
            TopicArn=sns_arn,
            Message=message
        )

        print(response)

    except Exception as e:
        print("ERROR PUBLISHING MESSAGE TO SNS: {}".format(e))


def read_tickers(file='stock_tickers.txt', period='5y'):
    pairs = dict()
    out_string = "\nINDIVIDUAL STATS:\n"

    with open(file, 'r') as f:
        while True:
            temp_string = ""
            try:
                # Get next line from file
                ticker = (f.readline()).strip()

                if ticker == "":
                    break

                stock = yf.Ticker(ticker)
                data = stock.history(env.get('PERIOD', period))

                close = data.Close[-1]
                temp_string += "{} Close: {}\n".format(ticker, str(close))

                high = max(data.Close)
                temp_string += "{} {}-High: {}\n".format(ticker, env.get('PERIOD', period), str(highh))

                delta = calc_stock(high, close)

                temp_string += "{} Delta: {}\n".format(ticker, str(delta))

                out_string += "\n" + temp_string

                pairs[ticker] = delta

                if not ticker:
                    break

            except Exception as e:
                print(e)
                if not ticker:
                    break

    return out_string, sorted(pairs.items(), key=lambda x: x[1])


def handler(event, context):
    """
    This function drives the AWS lambda. Requires 1 env var to work correctly: SNS_TOPIC which represents the topic arn to which
    you want to publish. 
    """

    out_string, pairs = read_tickers()
    message = create_message(pairs)
    message += out_string
    print(message)
    publish_message_sns(message)
    return message

