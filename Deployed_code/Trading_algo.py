import datetime
import requests
import json
import io
import pandas as pd
from random import choice
from google.cloud import storage
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def read_csv_from_cloud_storage(bucket_name, file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    
    content = blob.download_as_text()
    df = pd.read_csv(io.StringIO(content))
    
    return df

def update_and_replace_csv_in_cloud_storage(bucket_name, file_name, updated_df):
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    
    updated_content = updated_df.to_csv(index=False)
    blob.upload_from_string(updated_content)
    
    return "File updated and replaced successfully"

def get_data_for_current_day():

    USER_AGENTS = [
        # Chrome on Windows 10
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
        # Firefox on Macos
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12.4; rv:100.0) Gecko/20100101 Firefox/100.0",
    ]
    user_agent = choice(USER_AGENTS)
    headers = {
                "User-Agent": user_agent,
            }

    current_date = datetime.date.today() - datetime.timedelta(days=1)

    data = pd.DataFrame()

    try: 
        request = requests.get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata/' + str(current_date), headers=headers)
        r = request.json()['fear_and_greed_historical']['data'][0]
        data['Date'] = [current_date]
        data['index'] = [r['y']]
        data['pull_call_ratio'] = [request.json()['put_call_options']['data'][0]['y']]

    except:
        print(f"Data not available for {current_date}")

    return data


class FearandGreedIndexStrategy:
    def __init__(self,fear_data):
        self.data = None
        self.fear_data = fear_data

     # Download data from yfinance
    def load_data(self, symbol, start_date, end_date):
        print(symbol)
        self.data = yf.download(symbol,start_date, end_date).reset_index()

    def fear_category(self,x):
        if x <= 25:
            return "Extreme fear"
        elif (x <= 50) and (x > 25):
            return "Fear"
        elif (x <= 75) and (x > 50):
            return "Greed"
        elif (x <= 100) and (x > 75):
            return "Extreme Greed"
        
    def calculate_rsi(self, data, period=21):
        Close_prices = data['index']
        price_changes = Close_prices.diff()

        gains = price_changes.mask(price_changes < 0, 0)
        losses = -price_changes.mask(price_changes > 0, 0)

        average_gain = gains.rolling(window=period).mean()
        average_loss = losses.rolling(window=period).mean()

        rs = average_gain / average_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi
    
    # STOCHASTIC OSCILLATOR CALCULATION

    def get_stoch_osc(self, high, low, close, k_lookback, d_lookback):
        lowest_low = low.rolling(k_lookback).min()
        highest_high = high.rolling(k_lookback).max()
        k_line = ((close - lowest_low) / (highest_high - lowest_low)) * 100
        d_line = k_line.rolling(d_lookback).mean()
        return k_line, d_line

    
    def generate_signals(self):
        Complete_df = pd.merge(self.fear_data, self.data, on='Date', how='inner').set_index('Date')
        Complete_df['signal'] = 0
        
        Complete_df['k'] = self.get_stoch_osc(Complete_df['High'], Complete_df['Low'], Complete_df['Close'], 21, 6)[0]
        Complete_df['d']= self.get_stoch_osc(Complete_df['High'], Complete_df['Low'], Complete_df['Close'], 21, 6)[1]
        Complete_df['Fear_Strength_index'] = self.calculate_rsi(Complete_df, period=21)
        
        Complete_df.dropna(inplace=True)

        condition = (Complete_df[['k', 'd']] <= [20, 20]).sum(axis=1) >= 1
        condition &= Complete_df['pull_call_ratio'] > 1
        condition &= Complete_df['Fear_Strength_index'] <= 60

        Complete_df['signal'] = condition.astype(int)
        
        return Complete_df


def send_email_with_dataframe(subject, dataframe, sender, recipients, password):
    # Convert the DataFrame to an HTML table
    html_table = dataframe.to_html(index=False)

    # Create a multipart message and set the appropriate headers
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ', '.join(recipients)

    # Set the HTML content of the email
    email_body = f"""
    <html>
    <body>
    <h2>5-Day Fear_index Trading:</h2>
    {html_table}
    </body>
    </html>
    """
    message.attach(MIMEText(email_body, "html"))

    # Connect to the SMTP server and send the email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipients, message.as_string())
    print("Message sent!")




## updating the data
def trade_trigger(request):
  subject = " SPY stock market alert table"
  sender = "tradingbotwichita@gmail.com"
  recipients = ["tradingbotwichita@gmail.com", "bvnd.sai321@gmail.com"]
  password = "dufscwypfsxebszu"

  bucket_name = 'historicaltradingdata'
  file_name = 'fearindex_pull_ratio_2021.csv'

  updated_df = pd.concat([read_csv_from_cloud_storage(bucket_name, file_name),get_data_for_current_day()],axis=0).reset_index(drop=True).drop_duplicates()
  updated_df['Date'] = pd.to_datetime(updated_df['Date'])
  updated_df.drop_duplicates(inplace=True)
  update_and_replace_csv_in_cloud_storage(bucket_name, file_name, updated_df)

  # Initiate Backtesting and Load Data
  strategy = FearandGreedIndexStrategy(fear_data = updated_df)
  strategy.load_data('SPY', '2021-01-01' ,str(datetime.date.today()))
  results = strategy.generate_signals()


  # Example usage:
  # Create a sample DataFrame or use your own 'dataframe' DataFrame
  dataframe = results[['index', 'pull_call_ratio','Close','signal']].reset_index().tail(5)

  # Send the email with the DataFrame table
  send_email_with_dataframe(subject, dataframe, sender, recipients, password)

