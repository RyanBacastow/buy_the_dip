# buy_the_dip
This is a lambda function designed to give you an idea of price movements of your securities for the following purposes:
1) Researching stocks current market value versus their historical highs
2) Monitoring your portfolio assets versus some historical period
3) Useful info when seeking to sell at a 'high' and buy at a 'low'

The setup is designed to be deployed on AWS Lambda with 2 environment variables:
SNS_TOPIC: string value of the AWS SNS topic which your email or phone is subscribed to for this function.
PERIOD: string value, valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max

Simply add or remove assets from the stock_tickers.txt file.
