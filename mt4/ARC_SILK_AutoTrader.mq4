//+------------------------------------------------------------------+
//| ARC_SILK_AutoTrader.mq4                                          |
//| Demo-only moving-average crossover EA with ATR risk controls.     |
//| Safety: refuses non-demo accounts; no martingale/grid.            |
//+------------------------------------------------------------------+
#property strict
#property version   "0.2.0"
#property description "ARC_SILK demo-only MA crossover with ATR risk controls."

// Demo trading remains OFF by default. Never use this EA on a live account.
input bool            EnableDemoTrading = false;
input int             MagicNumber = 26102509;
input ENUM_TIMEFRAMES SignalTimeframe = PERIOD_M15;
input int             FastMAPeriod = 20;
input int             SlowMAPeriod = 50;
input int             ATRPeriod = 14;
input double          ATRStopMultiplier = 2.0;
input double          RewardRiskRatio = 2.0;
input double          RiskPercent = 0.5;
input double          MaxDailyLossPercent = 2.0;
input int             MaxSpreadPoints = 25;
input int             SlippagePoints = 10;
input int             MaxOpenPositions = 1;

datetime g_lastBar = 0;

//+------------------------------------------------------------------+
string DailyEquityKey()
{
   string key = "AS_DAILY_EQ_" + IntegerToString(AccountNumber()) + "_" +
                TimeToString(TimeCurrent(), TIME_DATE);
   StringReplace(key, ".", "");
   StringReplace(key, "-", "");
   return(key);
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(!IsDemo())
   {
      Print("ARC_SILK SAFETY BLOCK: this EA is demo-account only.");
      return(INIT_FAILED);
   }

   if(FastMAPeriod < 2 || SlowMAPeriod <= FastMAPeriod ||
      ATRPeriod < 2 || ATRStopMultiplier <= 0.0 || RewardRiskRatio <= 0.0 ||
      RiskPercent <= 0.0 || RiskPercent > 0.5 ||
      MaxDailyLossPercent <= 0.0 || MaxDailyLossPercent > 2.0 ||
      MaxSpreadPoints <= 0 || MaxOpenPositions < 1)
   {
      Print("ARC_SILK: invalid settings; fail closed.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   string key = DailyEquityKey();
   if(!GlobalVariableCheck(key) && !GlobalVariableSet(key, AccountEquity()))
   {
      Print("ARC_SILK: could not establish account-wide daily equity baseline.");
      return(INIT_FAILED);
   }

   g_lastBar = iTime(Symbol(), SignalTimeframe, 0);
   if(!EnableDemoTrading)
      Print("ARC_SILK loaded safely: demo trading disabled. Enable only on a demo account.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(!IsDemo() || !EnableDemoTrading || !IsTradeAllowed())
      return;

   if(!HasEnoughBars() || DailyLossLimitReached())
      return;

   RefreshRates();
   if(MarketInfo(Symbol(), MODE_SPREAD) > MaxSpreadPoints)
      return;

   if(!IsNewSignalBar())
      return;

   if(CountOpenPositionsByMagic() >= MaxOpenPositions)
      return;

   int direction = GetClosedBarCrossDirection();
   if(direction == 0)
      return;

   double atr = iATR(Symbol(), SignalTimeframe, ATRPeriod, 1);
   if(atr <= 0.0 || atr == EMPTY_VALUE)
      return;

   TryOpen(direction, atr);
}

//+------------------------------------------------------------------+
bool HasEnoughBars()
{
   int requiredBars = MathMax(SlowMAPeriod, ATRPeriod) + 3;
   return(iBars(Symbol(), SignalTimeframe) >= requiredBars);
}

//+------------------------------------------------------------------+
bool IsNewSignalBar()
{
   datetime barTime = iTime(Symbol(), SignalTimeframe, 0);
   if(barTime <= 0 || barTime == g_lastBar)
      return(false);
   g_lastBar = barTime;
   return(true);
}

//+------------------------------------------------------------------+
int GetClosedBarCrossDirection()
{
   double fastPrevious = iMA(Symbol(), SignalTimeframe, FastMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 2);
   double fastLast = iMA(Symbol(), SignalTimeframe, FastMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);
   double slowPrevious = iMA(Symbol(), SignalTimeframe, SlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 2);
   double slowLast = iMA(Symbol(), SignalTimeframe, SlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);

   if(fastPrevious <= 0.0 || fastLast <= 0.0 || slowPrevious <= 0.0 || slowLast <= 0.0)
      return(0);

   if(fastPrevious <= slowPrevious && fastLast > slowLast)
      return(1);
   if(fastPrevious >= slowPrevious && fastLast < slowLast)
      return(-1);
   return(0);
}

//+------------------------------------------------------------------+
int CountOpenPositionsByMagic()
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

//+------------------------------------------------------------------+
bool DailyLossLimitReached()
{
   // Account-wide daily baseline shared by every symbol/chart using this account.
   string key = DailyEquityKey();
   if(!GlobalVariableCheck(key))
   {
      Print("ARC_SILK: daily equity baseline missing; fail closed.");
      return(true);
   }

   double baseline = GlobalVariableGet(key);
   if(baseline <= 0.0)
      return(true);

   double lossPercent = 100.0 * (baseline - AccountEquity()) / baseline;
   if(lossPercent >= MaxDailyLossPercent)
   {
      Print("ARC_SILK: daily equity loss limit reached (", DoubleToString(lossPercent, 2),
            "%). New entries blocked; existing positions are not automatically closed.");
      return(true);
   }
   return(false);
}

//+------------------------------------------------------------------+
int LotDigits(double step)
{
   for(int digits = 0; digits <= 8; digits++)
      if(MathAbs(step - NormalizeDouble(step, digits)) < 1e-8)
         return(digits);
   return(2);
}

//+------------------------------------------------------------------+
double LotsForRisk(double stopDistance, int orderType)
{
   if(stopDistance <= 0.0)
      return(0.0);

   double equity = AccountEquity();
   double riskMoney = equity * RiskPercent / 100.0;
   double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSizePoints = MarketInfo(Symbol(), MODE_TICKSIZE);
   double tickSizePrice = tickSizePoints * Point;

   if(equity <= 0.0 || riskMoney <= 0.0 || tickValue <= 0.0 || tickSizePrice <= 0.0)
      return(0.0);

   double lossPerLot = (stopDistance / tickSizePrice) * tickValue;
   if(lossPerLot <= 0.0)
      return(0.0);

   double minLot = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
   double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
   if(lotStep <= 0.0 || minLot <= 0.0 || maxLot < minLot)
      return(0.0);

   // Floor to the broker lot step. Do not force the minimum lot if it exceeds risk.
   double lots = MathFloor((riskMoney / lossPerLot) / lotStep + 1e-8) * lotStep;
   lots = NormalizeDouble(lots, LotDigits(lotStep));
   if(lots < minLot || lots > maxLot)
      return(0.0);

   ResetLastError();
   double marginAfter = AccountFreeMarginCheck(Symbol(), orderType, lots);
   if(marginAfter <= 0.0 || GetLastError() == 134)
      return(0.0);

   return(lots);
}

//+------------------------------------------------------------------+
bool StopsMeetBrokerRules(double entry, double sl, double tp)
{
   double minimumDistance = MarketInfo(Symbol(), MODE_STOPLEVEL) * Point;
   if(minimumDistance < 0.0)
      return(false);
   if(MathAbs(entry - sl) < minimumDistance || MathAbs(entry - tp) < minimumDistance)
      return(false);
   return(true);
}

//+------------------------------------------------------------------+
void TryOpen(int direction, double atr)
{
   if(!IsDemo() || !EnableDemoTrading || !IsTradeAllowed() ||
      IsTradeContextBusy() || DailyLossLimitReached())
      return;

   int orderType = direction > 0 ? OP_BUY : OP_SELL;
   RefreshRates();
   double entry = direction > 0 ? Ask : Bid;
   if(entry <= 0.0)
      return;

   double brokerMinimum = (MarketInfo(Symbol(), MODE_STOPLEVEL) + 2.0) * Point;
   double stopDistance = MathMax(atr * ATRStopMultiplier, brokerMinimum);
   if(stopDistance <= 0.0)
      return;

   double targetDistance = stopDistance * RewardRiskRatio;
   int digits = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double sl = NormalizeDouble(direction > 0 ? entry - stopDistance : entry + stopDistance, digits);
   double tp = NormalizeDouble(direction > 0 ? entry + targetDistance : entry - targetDistance, digits);

   if(!StopsMeetBrokerRules(entry, sl, tp))
      return;

   double lots = LotsForRisk(stopDistance, orderType);
   if(lots <= 0.0)
   {
      Print("ARC_SILK: lot size invalid/below minimum or margin insufficient; no order sent.");
      return;
   }

   ResetLastError();
   int ticket = OrderSend(Symbol(), orderType, lots, NormalizeDouble(entry, digits),
                          SlippagePoints, sl, tp, "ARC_SILK demo MA/ATR",
                          MagicNumber, 0, clrNONE);
   if(ticket < 0)
      Print("ARC_SILK: OrderSend failed; error=", GetLastError());
   else
      Print("ARC_SILK demo order opened. Ticket=", ticket, ", lots=", DoubleToString(lots, LotDigits(MarketInfo(Symbol(), MODE_LOTSTEP))));
}
//+------------------------------------------------------------------+
