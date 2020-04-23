#!/usr/bin/env python
# coding: utf-8

from os import environ as env
import boto3
import yfinance as yf
import pandas as pd


def calc_stock(high, current):
    """
    :param high: float
    :param current: float
    :return: ratio: float
    """
    ratio = round(((current - high) / high) * 100, 2)
    return ratio


def convert_tuple(tup):
    """
    :param tup: tuple: tuple containing ranked pairs
    :return: string_tup: str: stringified version of incoming tuple
    """
    string_tup = f"{tup[0]} : {tup[1]}"
    return string_tup


def create_message(pairs, mode='personal'):
    """
    :param pairs: dict: contains ranked pairs
    :return: message: str: string of ranked pairs
    """
    if mode != 'legend':
        message = f"\n\n{mode.upper()} ORDERED RATIOS:\n\n"
        for pair in pairs:
            message += convert_tuple(pair) + "\n"
    else:
        message = "\n\nS&P TICKER LEGEND\n\n"
        for company in pairs:
            message += f"{company} : {pairs[company]}\n"

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

    except Exception as e:
        print(f"ERROR PUBLISHING MESSAGE TO SNS: {e}")


def get_data(tickers_list, period):
    """
    :param tickers: str: stock ticker string
    :param period: str: valid date period for comparison
    :return: temp_string, delta: str, float: stock printing statements and ratio are returned
    """
    pairs = dict()
    temp_string = ""
    tickers = " ".join([x.upper() for x in tickers_list]).strip()
    stocks = yf.Tickers(tickers)
    data = stocks.history(env.get('PERIOD', period))['Close']

    for ticker in tickers_list:
        try:
            df = data[ticker]
            df.dropna(inplace=True)
            close = df[-1]
            close_date = df.index[-1]
            temp_string += f"{ticker} Close {close_date.strftime('%Y-%m-%d')}: {close:.2f}\n"

            high = max(df)
            temp_string += f"{ticker} {env.get('PERIOD', period)}-High: {high:.2f}\n"

            delta = calc_stock(high, close)
            pairs[ticker] = delta

            temp_string += f"{ticker} Delta: {delta}\n\n"
        except KeyError as ke:
            print(f"Couldn't find {ticker} in data")

    return temp_string, pairs


def read_tickers(mode='period', period='5y'):
    """
    :param mode: str: personal will use personal_portfolio_stock_tickers.txt. Any other mode will simply use the S&P500
    :param period: str: valid period.
    :return: out_string,sorted(pairs.items(), key=lambda x: x[1]): str, list: string for message and sorted dict in list
    """

    if mode == 'personal':
        out_string = "\n\nPERSONAL PORTFOLIO INDIVIDUAL HOLDING STATS:\n\n"
        tickers_list = []
        print(f"\nRunning program on personal portfolio with period {period}...\n")
        with open('personal_portfolio_stock_tickers.txt', 'r') as f:
            while True:
                ticker = (f.readline()).strip()
                if ticker == "":
                    break
                tickers_list.append(ticker)
                if not ticker:
                    break
            try:
                temp_string, pairs = get_data(tickers_list, period)
                out_string += temp_string

            except Exception as e:
                print(e)
                print(f"ERROR WITH TICKER {ticker}: {e}")

        return out_string, sorted(pairs.items(), key=lambda x: x[1])

    else:
        out_string = "\n\n"
        print(f"\nRunning program on full S&P with period {period}...\n")
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = table[0]
        df['Symbol'] = df['Symbol'].str.replace('.', '')
        company_names = dict(zip(df.Symbol, df.Security))
        tickers_list = [x for x in df.Symbol]

        try:
            temp_string, pairs = get_data(tickers_list, period)
            out_string += temp_string

        except Exception as e:
            print(e)

        return out_string, sorted(pairs.items(), key=lambda x: x[1]), company_names


def handler(event, context):
    """
    This function drives the AWS lambda. Requires 1 env var to work correctly: SNS_TOPIC which represents the topic arn
    to which you want to publish.
    """
    personal_string, personal_pairs = read_tickers(mode='personal', period='10d')
    message = create_message(personal_pairs, mode='personal')
    message += personal_string + "\n\n––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––\n\n"

    snp_string, snp_pairs, company_names = read_tickers(mode='S&P', period='10d')
    message += create_message(snp_pairs, 'S&P')

    message += "\n\n––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––\n\n"
    message += create_message(company_names, mode='legend')
    publish_message_sns(message)
    return message
