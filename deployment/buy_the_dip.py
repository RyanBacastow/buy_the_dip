#!/usr/bin/env python
# coding: utf-8
from os import environ as env
import boto3
import yfinance as yf
import pandas as pd
from datetime import datetime
from urllib.request import urlopen
from contextlib import closing
import json
import traceback

sep = '\n-----------------------------------------------------------------\n\n'


def calc_stock(high, current):
    """
    :param high: float
    :param current: float
    :return: ratio: float
    """
    ratio = round(((current - high) / high) * 100, 2)
    return ratio


def create_message(pairs, mode='personal', company_names={}):
    """
    :param pairs: dict: contains ranked pairs
    :return: message: str: string of ranked pairs
    """
    print("begin create_message")
    message = f"\n{mode.upper()} ORDERED RATIOS:\n"

    for k, v in pairs:
        try:
            company_name = company_names[k]
            new_pair = f"{k} ({company_name}) : {v}"
            message += new_pair + "\n"
        except KeyError as e:
            print(e)
            print(f"Couldn't find {k} in company_names")
            message += f"{k} : {v}\n"

    return message


def publish_message_sns(message):
    """
    :param message: str: message to be sent to SNS
    :return: None
    """
    print("begin publish_message_sns")
    sns_arn = env.get('SNS_ARN').strip()
    sns_client = boto3.client('sns')
    try:
        response = sns_client.publish(
            TopicArn=sns_arn,
            Message=message
        )

    except Exception as e:
        print(f"ERROR PUBLISHING MESSAGE TO SNS: {e}")


def get_data(tickers_list, period, company_names):
    """
    :param tickers: str: stock ticker string
    :param period: str: valid date period for comparison
    :return: temp_string, delta: str, float: stock printing statements and ratio are returned
    """
    print("begin get_data")
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

            try:
                temp_string += f"{ticker} ({company_names[ticker]}) Close {close_date.strftime('%Y-%m-%d')}: {close:.2f}\n"
            except:
                temp_string += f"{ticker} Close {close_date.strftime('%Y-%m-%d')}: {close:.2f}\n"

            high = max(df)
            temp_string += f"{ticker} {env.get('PERIOD', period)}-High: {high:.2f}\n"

            delta = calc_stock(high, close)
            pairs[ticker] = delta

            temp_string += f"{ticker} Delta: {delta}\n\n"
        except keyerror as e:
            print(f"Couldn't find {ticker} in data")

    print("end get_data")
    return temp_string, pairs

def read_tickers(mode='personal', period='5y'):
    """
    :param mode: str: personal will use personal_portfolio_stock_tickers.txt. Any other mode will simply use the S&P500
    :param period: str: valid period.
    :return: out_string,sorted(pairs.items(), key=lambda x: x[1]): str, list: string for message and sorted dict in list
    """
    print("begin read_tickers")

    sp_table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    sp_df = sp_table[0]
    sp_df['Symbol'] = sp_df['Symbol'].str.replace('.', '')
    sp_company_names = dict(zip(sp_df.Symbol, sp_df.Security))

    nsdq_table = pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100")
    nsdq_df = nsdq_table[2]
    nsdq_df['Ticker'] = nsdq_df['Ticker'].str.replace('.', '')
    nsdq_df.rename(columns={"Ticker": "Symbol", "Company": "Security"}, inplace=True)
    nsdq_company_names = dict(zip(nsdq_df.Symbol, nsdq_df.Security))

    company_names = dict()
    company_names.update(sp_company_names)
    company_names.update(nsdq_company_names)

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
                temp_string, pairs = get_data(tickers_list, period, company_names)
                out_string += temp_string

            except Exception as e:
                print(e)
                print(f"ERROR WITH TICKER {ticker}: {e}")

    else:
        out_string = "\n\n"
        print(f"\nRunning program on full {mode.lower()} with period {period}...\n")

        if mode.lower() == 'nsdq':
            tickers_list = [x for x in nsdq_df.Symbol]
        else:
            tickers_list = [x for x in sp_df.Symbol]

        try:
            temp_string, pairs = get_data(tickers_list, period, company_names)
            out_string += temp_string

        except Exception as e:
            print(e)

    print("end read_tickers")
    return out_string, sorted(pairs.items(), key=lambda x: x[1]), company_names


def index_checker():
    final_string = f"""Checked indexes and stocks at {datetime.utcnow()} UTC.\n\n"""
    final_string += """INDEXES\n"""

    try:
        url = "https://financialmodelingprep.com/api/v3/majors-indexes/"
        print(f"Attempting get data from {url}")
        with closing(urlopen(url)) as responseData:
            json_data = responseData.read()
            deserialised_data = json.loads(json_data)
        market_indicator_total = 0.0
        market_indicator_ratio = 0.0
        for ticker in deserialised_data['majorIndexesList']:
            ticker_name = ticker['ticker']
            price = ticker['price']
            price_change = ticker['changes']
            price_change_ratio = (price_change / price) * 100
            full_ticker_name = ticker['indexName']
            change_float = float(price_change)
            market_indicator_total += change_float
            market_indicator_ratio += price_change_ratio
            if change_float > 0:
                price_change_type = 'upward'
            elif change_float < 0:
                price_change_type = 'downward'
            else:
                price_change_type = 'neutral'

            final_string += f"The {full_ticker_name} index (ticker:{ticker_name}) trended {price_change_type} {price_change} points, {price_change_ratio:.2f}%.\n"

        final_string += f"\nAll indexes moved a cumulative sum of {market_indicator_total:.2f} points and {market_indicator_ratio:.2f}%\n"

    except Exception as e:
        print(e)

    return final_string


def handler(event, context):
    """
    This function drives the AWS lambda. Requires 1 env var to work correctly: SNS_TOPIC which represents the topic arn
    to which you want to publish.
    """
    message = index_checker()

    personal_string, personal_pairs, company_names = read_tickers(mode='personal', period='10d')
    message += sep + "RATIOS\n" "\nRatios can be interpreted as percentages ranging from -99.99 representing a total loss of value, to 0.00 which represents a stock is at its high point for the period selected.\n"
    message += create_message(personal_pairs, mode='personal', company_names=company_names) + sep
    message += personal_string + sep
    nsdq_string, nsdq_pairs, company_names = read_tickers(mode='NSDQ', period='10d')
    message += create_message(nsdq_pairs, mode='S&P', company_names=company_names)
    snp_string, snp_pairs, company_names = read_tickers(mode='S&P', period='10d')
    message += create_message(snp_pairs, mode='S&P', company_names=company_names)
    publish_message_sns(message)

    return message
