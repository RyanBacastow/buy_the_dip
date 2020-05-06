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
import wget

sep = '\n--------------------------------------------------------------------------------------------\n'

all_company_names = dict()

sp_table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
sp_df = sp_table[0]
sp_df['Symbol'] = sp_df['Symbol'].str.replace('.', '')
sp_company_names = dict(zip(sp_df.Symbol, sp_df.Security))

nsdq_table = pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100")
nsdq_df = nsdq_table[2]
nsdq_df['Ticker'] = nsdq_df['Ticker'].str.replace('.', '')
nsdq_df.rename(columns={"Ticker": "Symbol", "Company": "Security"}, inplace=True)
nsdq_company_names = dict(zip(nsdq_df.Symbol, nsdq_df.Security))

link = 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt'
wget.download(link, out='tmp')
nsdq_full_df = pd.read_csv('tmp/nasdaqlisted.txt', sep='|', header=0)
nsdq_full_df.drop(nsdq_full_df.tail(1).index, inplace=True)
nsdq_full_company_names = dict(zip(nsdq_full_df.Symbol, nsdq_full_df['Security Name']))
for k, v in nsdq_full_company_names.items():
    nsdq_full_company_names[k] = v.split(' - ')[0]

for d in [sp_company_names, nsdq_company_names, nsdq_full_company_names]:
    all_company_names.update(d)


def calc_stock(high, current):
    """
    :param high: float
    :param current: float
    :return: ratio: float
    """
    ratio = round(((current - high) / high) * 100, 2)
    return ratio


def create_message(pairs, mode='personal', company_names=all_company_names, period="1y"):
    """
    :param pairs: list: contains ranked pairs
    :return: message: str: string of ranked pairs
    """
    if period.lower() in ["daily", "weekly", "monthly"]:
        message = f"\n{mode.upper()} 25 {period.upper()} BIGGEST LOSERS" + sep
    else:
        message = f"\nFULL {mode.upper()} ORDERED RATIOS PAST {period.upper()}" + sep

    for k, v in pairs:
        try:
            company_name = company_names[k]
            new_pair = f"{k} ({company_name}) : {v}"
            message += new_pair + "\n"
        except Exception as e:
            print(e)
            print(f"Couldn't find {k} in company_names")

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


def get_data(tickers_list, period, company_names=all_company_names):
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

    print(data.head())
    print(data.tail())

    for ticker in tickers_list:
        try:
            df = data[ticker]
            df.dropna(inplace=True)
            close = df[-1]
            high = max(df)
            delta = calc_stock(high, close)
            pairs[ticker] = delta

        except Exception as e:
            print(f"Couldn't find {ticker} in data")
    return pairs


def read_tickers(mode='personal', period='1y'):
    """
    :param mode: str: personal will use personal_portfolio_stock_tickers.txt. Any other mode will simply use the S&P500
    :param period: str: valid period.
    :return: sorted(pairs.items(), key=lambda x: x[1]): str, list: string for message and sorted dict in list
    """
    company_names = dict()
    company_names.update(sp_company_names)
    company_names.update(nsdq_company_names)

    if mode.lower() == 'personal':
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
                pairs = get_data(tickers_list, period)

            except Exception as e:
                print(e)
                print(f"ERROR WITH TICKER {ticker}: {e}")

    else:
        print(f"\nRunning program on full {mode.lower()} with period {period}...\n")

        if mode.lower() == 'nasdaq':
            tickers_list = [x for x in nsdq_df.Symbol]
        else:
            tickers_list = [x for x in sp_df.Symbol]

        pairs = get_data(tickers_list, period)

    return sorted(pairs.items(), key=lambda x: x[1])


def index_checker():
    final_string = f"""Checked indexes and stocks at {datetime.utcnow()} UTC.\n\n"""
    final_string += """\nINDEXES""" + sep

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
    This function drives the AWS lambda. Requires 1 env var to work correctly: SNS_TOPIC which represents the topic arn to which
    you want to publish.
    """
    message = index_checker()
    message += "\nRATIOS" + sep + """
                                 \nRatios can be interpreted as percentages ranging from -99.99 representing a total 
                                 loss of value, to 0.00 which represents that a stock is at its high point for 
                                 the period selected.\n 
                                  """

    daily_nsdq = read_tickers(mode="NASDAQ", period="2d")
    daily_nsdq = daily_nsdq[:24]

    message += create_message(daily_nsdq, mode='NASDAQ', period="daily")

    daily_snp = read_tickers(mode="S&P", period="2d")[:25]
    message += create_message(daily_snp, mode='S&P', period="daily")

    weekly_nsdq = read_tickers(mode="NASDAQ", period="1w")[:25]
    message += create_message(weekly_nsdq, mode='NASDAQ', period="weekly")

    weekly_snp = read_tickers(mode="S&P", period="6d")[:25]
    message += create_message(weekly_snp, mode='S&P', period="weekly")

    monthly_nsdq = read_tickers(mode="NASDAQ", period="6d")[:25]
    message += create_message(monthly_nsdq, mode='NASDAQ', period="monthly")

    monthly_snp = read_tickers(mode="S&P", period="1mo")[:25]
    message += create_message(monthly_snp, mode='S&P', period="monthly")

    personal_pairs = read_tickers(mode='personal', period=env.get('PERIOD', "1y"))

    message += create_message(personal_pairs, mode='personal', period="1y")

    nsdq_pairs = read_tickers(mode='NASDAQ', period=env.get('PERIOD', "1y"))
    message += create_message(nsdq_pairs, mode='NASDAQ', period="1y")

    snp_pairs = read_tickers(mode='S&P', period=env.get('PERIOD', "1y"))
    message += create_message(snp_pairs, mode='S&P', period="1y")

    publish_message_sns(message)
    return message
