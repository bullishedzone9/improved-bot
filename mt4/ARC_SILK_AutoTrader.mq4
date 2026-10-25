//+------------------------------------------------------------------+
//| ARC_SILK_AutoTrader.mq4                                          |
//| Conservative demo-only EMA crossover EA with ATR risk controls.  |
//| IMPORTANT: compile and test in MetaEditor/Strategy Tester first.  |
//+------------------------------------------------------------------+
#property strict
#property version   "0.2.0"
#property description "Demo-only EMA crossover EA. No live-account execution."

input bool            EnableDemoTrading       = false; // Must be manually enabled on a DEMO account
input int             MagicNumber             = 26102509;
input ENUM_TIMEFRAMES SignalTimeframe         = PERIOD_M15;
input int             FastMAPeriod            = 20;
input int             SlowMAPeriod            = 50;
input int             ATRPeriod               = 14;
input double          ATRStopMultiplier       = 2.0;
input double          RewardRiskRatio          = 2.0;
input double          RiskPercent              = 0.5;
input double          MaxDailyLossPercent      = 2.0;
input int             MaxSpreadPoints          = 25;
input int             SlippagePoints           = 10;
input int             MaxOpenPositions         = 1;   // Across this EA's magic number/account
input int             MaxRetries               = 2;   // Bounded retries only
input int             RetryDelayMilliseconds   = 500;

datetime g_lastBarTime = 0;
bool     g_dailyLock   = false;

//--------------------------------------------------------------------
int OnInit()
{
   if(!IsDemo())
   {
      Print("ARC_SILK EA BLOCKED: this EA only runs on a broker demo account.");
      return(INIT_FAILED);
   }

   if(FastMAPeriod < 2 || SlowMAPeriod <= FastMAPeriod ||
      ATRPeriod < 2 || ATRStopMultiplier <= 0 ||
      RewardRiskRatio <= 0 || RiskPercent <= 0 ||
      RiskPercent > 0.5 || MaxDailyLossPercent <= 0 ||
      MaxDailyLossPercent > 2.0 || MaxSpreadPoints < 0 ||
      MaxOpenPositions < 1 || MaxRetries < 0 || MaxRetries > 3)
   {
      Print("ARC_SILK EA BLOCKED: invalid or unsafe input configuration.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   if(!EnableDemoTrading)
      Print("ARC_SILK EA initialized in SAFE mode. EnableDemoTrading=false; no orders will be sent.");

   g_lastBarTime = iTime(Symbol(), SignalTimeframe, 0);
   EnsureDailyBaseline();
   Print("ARC_SILK demo-only EA initialized on ", Symbol(),
         " / timeframe ", EnumToString(SignalTimeframe),
         ". Order execution enabled: ", EnableDemoTrading);
   return(INIT_SUCCEEDED);
}

//--------------------------------------------------------------------
void OnTick()
{
   if(!IsDemo() || !EnableDemoTrading)
      return;

   if(!IsTradeAllowed() || IsTradeContextBusy())
      return;

   if(!EnsureDailyBaseline() || DailyLossLimitReached())
   {
      g_dailyLock = true;
      return;
   }
   if(g_dailyLock)
      return;

   if(!IsNewSignalBar())
      return;

   if(!MarketDataReady())
      return;

   if(MarketInfo(Symbol(), MODE_SPREAD) > MaxSpreadPoints)
   {
      Print("Signal skipped: spread exceeds configured maximum.");
      return;
   }

   if(CountOpenPositions() >= MaxOpenPositions)
      return;

   int direction = GetClosedBarCross();
   if(direction == 0)
      return;

   RefreshRates();
   double atr = iATR(Symbol(), SignalTimeframe, ATRPeriod, 1);
   if(atr <= 0 || !MathIsValidNumber(atr))
   {
      Print("Signal skipped: invalid ATR.");
      return;
   }

   TryOpen(direction, atr);
}

//--------------------------------------------------------------------
bool MarketDataReady()
{
   int requiredBars = SlowMAPeriod + 5;
   if(iBars(Symbol(), SignalTimeframe) < requiredBars)
      return(false);

   if(MarketInfo(Symbol(), MODE_BID) <= 0 || MarketInfo(Symbol(), MODE_ASK) <= 0)
      return(false);

   return(true);
}

//--------------------------------------------------------------------
bool IsNewSignalBar()
{
   datetime barTime = iTime(Symbol(), SignalTimeframe, 0);
   if(barTime <= 0 || barTime == g_lastBarTime)
      return(false);

   g_lastBarTime = barTime;
   return(true);
}

//--------------------------------------------------------------------
// Signals use only completed candles (shifts 2 and 1).
int GetClosedBarCross()
{
   double fast2 = iMA(Symbol(), SignalTimeframe, FastMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 2);
   double fast1 = iMA(Symbol(), SignalTimeframe, FastMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);
   double slow2 = iMA(Symbol(), SignalTimeframe, SlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 2);
   double slow1 = iMA(Symbol(), SignalTimeframe, SlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);

   if(fast2 <= 0 || fast1 <= 0 || slow2 <= 0 || slow1 <= 0)
      return(0);

   if(fast2 <= slow2 && fast1 > slow1)
      return(1);
   if(fast2 >= slow2 && fast1 < slow1)
      return(-1);

   return(0);
}

//--------------------------------------------------------------------
int CountOpenPositions()
{
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if(OrderMagicNumber() != MagicNumber)
         continue;
      if(OrderType() == OP_BUY || OrderType() == OP_SELL)
         count++;
   }
   return(count);
}

//--------------------------------------------------------------------
bool EnsureDailyBaseline()
{
   string day = TimeToString(TimeCurrent(), TIME_DATE);
   StringReplace(day, ".", "");
   StringReplace(day, "-", "");
   string key = "AS_DBASE_" + IntegerToString(AccountNumber()) + "_" + day;

   if(!GlobalVariableCheck(key))
   {
      // First EA initialization/tick on a given server day becomes the baseline.
      // For reliable day-start loss accounting, keep MT4 running and verify this
      // baseline against the account's day-start equity before enabling demo orders.
      ResetLastError();
      if(GlobalVariableSet(key, AccountEquity()) == 0)
      {
         Print("Daily baseline could not be saved. Trading blocked. Error ", GetLastError());
         return(false);
      }
   }
   return(true);
}

//--------------------------------------------------------------------
double DailyBaseline()
{
   string day = TimeToString(TimeCurrent(), TIME_DATE);
   StringReplace(day, ".", "");
   StringReplace(day, "-", "");
   string key = "AS_DBASE_" + IntegerToString(AccountNumber()) + "_" + day;
   if(!GlobalVariableCheck(key))
      return(0);
   return(GlobalVariableGet(key));
}

//--------------------------------------------------------------------
bool DailyLossLimitReached()
{
   double baseline = DailyBaseline();
   if(baseline <= 0)
      return(true);

   double lossPercent = (baseline - AccountEquity()) / baseline * 100.0;
   if(lossPercent >= MaxDailyLossPercent)
   {
      Print("DAILY LOSS LOCK: equity drawdown from saved daily baseline is ",
            DoubleToString(lossPercent, 2), "%. No new entries allowed.");
      return(true);
   }
   return(false);
}

//--------------------------------------------------------------------
double NormalizeLotsDown(double lots)
{
   double minLot = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);

   if(lotStep <= 0 || minLot <= 0 || maxLot < minLot)
      return(0);

   lots = MathMin(lots, maxLot);
   lots = MathFloor(lots / lotStep + 1e-8) * lotStep;
   lots = NormalizeDouble(lots, 3);

   // Never round up to the broker minimum if it exceeds calculated risk.
   if(lots < minLot)
      return(0);
   return(lots);
}

//--------------------------------------------------------------------
double LotsForRisk(double stopDistancePrice)
{
   if(stopDistancePrice <= 0)
      return(0);

   double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSizePoints = MarketInfo(Symbol(), MODE_TICKSIZE);
   if(tickValue <= 0 || tickSizePoints <= 0 || Point <= 0)
      return(0);

   double tickSizePrice = tickSizePoints * Point;
   if(tickSizePrice <= 0)
      return(0);

   double lossPerLot = (stopDistancePrice / tickSizePrice) * tickValue;
   if(lossPerLot <= 0 || !MathIsValidNumber(lossPerLot))
      return(0);

   double riskMoney = AccountEquity() * (RiskPercent / 100.0);
   if(riskMoney <= 0)
      return(0);

   return(NormalizeLotsDown(riskMoney / lossPerLot));
}

//--------------------------------------------------------------------
void TryOpen(int direction, double atr)
{
   RefreshRates();
   double ask = MarketInfo(Symbol(), MODE_ASK);
   double bid = MarketInfo(Symbol(), MODE_BID);
   if(ask <= 0 || bid <= 0 || ask < bid)
      return;

   double stopDistance = atr * ATRStopMultiplier;
   double stopLevel = MarketInfo(Symbol(), MODE_STOPLEVEL) * Point;
   double freezeLevel = MarketInfo(Symbol(), MODE_FREEZELEVEL) * Point;
   double minDistance = MathMax(stopLevel, freezeLevel) + (2.0 * Point);

   if(stopDistance < minDistance)
   {
      Print("Signal skipped: ATR stop distance is below broker minimum.");
      return;
   }

   double entry = (direction > 0) ? ask : bid;
   double sl = (direction > 0) ? entry - stopDistance : entry + stopDistance;
   double tpDistance = stopDistance * RewardRiskRatio;
   double tp = (direction > 0) ? entry + tpDistance : entry - tpDistance;

   int digits = (int)MarketInfo(Symbol(), MODE_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   entry = NormalizeDouble(entry, digits);

   double lots = LotsForRisk(MathAbs(entry - sl));
   if(lots <= 0)
   {
      Print("Signal skipped: safe lot size cannot be calculated within risk budget.");
      return;
   }

   ResetLastError();
   double freeMargin = AccountFreeMarginCheck(Symbol(), direction > 0 ? OP_BUY : OP_SELL, lots);
   int marginError = GetLastError();
   if(freeMargin <= 0 || marginError == 134)
   {
      Print("Signal skipped: insufficient free margin.");
      return;
   }

   // Re-check spread and demo status immediately before sending.
   if(!IsDemo() || MarketInfo(Symbol(), MODE_SPREAD) > MaxSpreadPoints)
      return;

   int orderType = (direction > 0) ? OP_BUY : OP_SELL;
   string comment = "ARC_SILK demo EA";
   int ticket = -1;

   for(int attempt = 0; attempt <= MaxRetries; attempt++)
   {
      if(!IsDemo() || !EnableDemoTrading || !IsTradeAllowed())
         return;

      RefreshRates();
      entry = NormalizeDouble((direction > 0) ? Ask : Bid, digits);
      // Recalculate SL/TP around the refreshed entry while preserving distance.
      sl = NormalizeDouble((direction > 0) ? entry - stopDistance : entry + stopDistance, digits);
      tp = NormalizeDouble((direction > 0) ? entry + tpDistance : entry - tpDistance, digits);

      ResetLastError();
      ticket = OrderSend(Symbol(), orderType, lots, entry, SlippagePoints, sl, tp,
                         comment, MagicNumber, 0, clrNONE);
      if(ticket >= 0)
      {
         Print("DEMO order accepted. Ticket=", ticket, " lots=", DoubleToString(lots, 3),
               " entry=", DoubleToString(entry, digits),
               " SL=", DoubleToString(sl, digits), " TP=", DoubleToString(tp, digits));
         return;
      }

      int err = GetLastError();
      Print("OrderSend failed on attempt ", attempt + 1, ". Error=", err);
      // Retry only transient errors; avoid duplicating orders after ambiguous responses.
      if(err != 4 && err != 6 && err != 136 && err != 137 && err != 146)
         break;
      if(attempt < MaxRetries)
         Sleep(RetryDelayMilliseconds);
   }

   Print("No order opened. Review MT4 Experts/Journal logs.");
}
//+------------------------------------------------------------------+
