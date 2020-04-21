#!/usr/bin/env python
# coding: utf-8

from os import environ as env
import boto3
import yfinance as yf
import pandas as pd


# !/usr/bin/env python
# coding: utf-8


def calc_stock(high, current):
    """
    :param high: float
    :param current: float
    :return: ratio: float
    """
    ratio = (current - high) / high
    return ratio


def convert_tuple(tup):
    """
    :param tup: tuple: tuple containing ranked pairs
    :return: string_tup: str: stringified version of incoming tuple
    """
    string_tup = "{} : {}".format(tup[0], str(tup[1]))
    return string_tup


def create_message(pairs, mode='personal'):
    """
    :param pairs: dict: contains ranked pairs
    :return: message: str: string of ranked pairs
    """
    message = "\n\n{} ORDERED RATIOS:\n\n".format(mode.upper())
    for pair in pairs:
        message += convert_tuple(pair) + "\n"
    return message


def publish_message_sns(message):
    """
    :param message: str: message to be sent to SNS
    :return: None
    """
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


def get_data(ticker, period):
    """
    :param ticker: str: stock ticker
    :param period: str: valid date period for comparison
    :return: temp_string, delta: str, float: stock printing statements and ratio are returned
    """
    temp_string = ""
    stock = yf.Ticker(ticker)
    data = stock.history(env.get('PERIOD', period))

    close = data.Close[-1]
    close_date = data.index[-1]
    temp_string += "{} Close {}: {}\n".format(ticker, str(close_date), str(close))

    high = max(data.Close)
    temp_string += "{} {}-High: {}\n".format(ticker, env.get('PERIOD', period), str(high))

    delta = calc_stock(high, close)

    temp_string += "{} Delta: {}\n".format(ticker, str(delta)) + "\n"

    return temp_string, delta


def read_tickers(mode='personal', period='1y'):
    """
    :param mode: str: personal will use personal_portfolio_stock_tickers.txt. Any other mode will simply use the S&P500
    :param period: str: valid period.
    :return: out_string,sorted(pairs.items(), key=lambda x: x[1]): str, list: string for message and sorted dict in list
    """
    pairs = dict()
    out_string = "\n\nPERSONAL PORTFOLIO INDIVIDUAL STATS:\n\n"

    if mode == 'personal':
        print("\nRunning program on personal portfolio with period {}...\n".format(period))
        with open('personal_portfolio_stock_tickers.txt', 'r') as f:
            while True:
                try:
                    ticker = (f.readline()).strip()
                    if ticker == "":
                        break

                    temp_string, delta = get_data(ticker, period)
                    out_string += temp_string

                    pairs[ticker] = delta
                    if not ticker:
                        break

                except Exception as e:
                    print("ERROR WITH TICKER {}: {}".format(ticker, e))
                    if not ticker:
                        break

    else:
        print("\nRunning program on full S&P with period {}...\n".format(period))
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = table[0]
        tickers = df.Symbol
        for ticker in tickers:
            if '.' in ticker:
                ticker = ticker.replace(".", "-")
            try:
                temp_string, delta = get_data(ticker, period)
                out_string += temp_string
                pairs[ticker] = delta

            except Exception as e:
                print("ERROR WITH TICKER {}: {}".format(ticker, e))

    return out_string, sorted(pairs.items(), key=lambda x: x[1])


def handler(event, context):
    """
    This function drives the AWS lambda. Requires 1 env var to work correctly: SNS_TOPIC which represents the topic arn
    to which you want to publish.
    """
    personal_string, personal_pairs = read_tickers(mode='personal', period='10d')
    message = create_message(personal_pairs, mode='personal')
    message += personal_string + "\n\n–––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––\n\n"

    snp_string, snp_pairs = read_tickers(mode='s&p', period='10d')
    message += create_message(snp_pairs, 'S&P')
    publish_message_sns(message)
    return message
