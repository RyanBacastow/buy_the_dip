# buy_the_dip
**This is a lambda function designed to give you an idea of price movements of your securities for the following purposes:**
1) Researching stocks current market value versus their historical highs
2) Monitoring your portfolio assets versus some historical period
3) Useful info when seeking to sell at a 'high' and buy at a 'low'

**The setup is designed to be deployed on AWS using three services:**
 - **Lambda** with 2 environment variables:
  	- SNS_TOPIC: string value of the AWS SNS topic which your email or phone is subscribed to for this function.
  	- PERIOD: string value, valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
 - **SNS Topic**: You will subscribe your email to the SNS Topic.
 - **Cloudwatch Event Trigger**: This will be how you trigger the function at the close of the NYSE each day.

*Simply add or remove assets from the stock_tickers.txt file to adjust which securities you'd like to get updates on.*

If you've never built a lambda -> SNS widget before, you can start with a tutorial [here](https://www.youtube.com/watch?v=PsJsP-7cydk).

Happy Hunting!