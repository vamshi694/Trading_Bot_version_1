
Creating a trading bot based on the Machine Learning Lorentzian Classification  
  
**Indicators**:  
Moving Average Exponential (**200 EMA**)  Or Rational Quadratic Kernel (Gaussian kernel to get trend  )
- Easy 
**SuperTrend** by Kivanc0zbilgic (ATR=15, Multiplier 10)  
- Medium article: https://levelup.gitconnected.com/step-by-step-implementation-of-the-supertrend-indicator-in-python-656aa678c111
Machine Learning: **Lorentzian** Classification by jdehorty  
- Should build on own
- KNN/ANN & Lorentzian distance + 5 features + ADX for better alerting
  
For a **sell**, the Lorentzian indicator must give sell signal. The close of the candle must be below the 200 ema, and the supertrend indicator must be red.  
  
For **buy**, the Lorentzian indicator must give buy signal. The close of the candle must be above the 200 ema, and the supertrend indicator must be green.
