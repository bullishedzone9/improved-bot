//+------------------------------------------------------------------+
//| ARC_SILK_AutoTrader.mq4                                          |
//| Demo-only moving-average crossover EA.                            |
//| Safety: refuses non-demo accounts; no martingale/grid.             |
//+------------------------------------------------------------------+
#property strict
#property version   "0.1.0"
#property description "ARC_SILK demo-only MA crossover with ATR risk controls."

input bool   EnableDemoTrading = false; // must be deliberately enabled on a demo account
input int    MagicNumber = 26102509;
input ENUM_TIMEFRAMES SignalTimeframe = PERIOD_M15;
input int    FastMAPeriod = 20;
input int    SlowMAPeriod = 50;
input int    ATRPeriod = 14;
input double ATRStopMultiplier = 2.0;
input double RewardRiskRatio = 2.0;
input double RiskPercent = 0.5;
input double MaxDailyLossPercent = 2.0;
input int    MaxSpreadPoints = 25;
input int    SlippagePoints = 10;

datetime g_lastBar = 0;
double g_dayStartEquity = 0;
int g_dayKey = -1;
bool g_dailyLocked = false;

int DateKey(datetime value) {
   return TimeYear(value) * 1000 + TimeDayOfYear(value);
}

void RefreshDailyGuard() {
   int key = DateKey(TimeCurrent());
   if(key != g_dayKey) {
      g_dayKey = key;
      g_dayStartEquity = AccountEquity();
      g_dailyLocked = false;
   }
   if(g_dayStartEquity <= 0) {
      g_dailyLocked = true;
      return;
   }
   double lossPct = (g_dayStartEquity - AccountEquity()) / g_dayStartEquity * 100.0;
   if(lossPct >= MaxDailyLossPercent) g_dailyLocked = true;
}

bool IsNewSignalBar() {
   datetime bar = iTime(Symbol(), SignalTimeframe, 0);
   if(bar <= 0 || bar == g_lastBar) return false;
   g_lastBar = bar;
   return true;
}

int CurrentPositionCount() {
   int count = 0;
   for(int i=OrdersTotal()-1; i>=0; i--) {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol() == Symbol() && OrderMagicNumber() == MagicNumber &&
         (OrderType() == OP_BUY || OrderType() == OP_SELL)) count++;
   }
   return count;
}

double NormalizeLots(double lots) {
   double minLot = MarketInfo(Symbol(), MODE_MINLOT);
   double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
   double step = MarketInfo(Symbol(), MODE_LOTSTEP);
   if(step <= 0 || minLot <= 0 || maxLot < minLot) return 0;
   lots = MathFloor(lots / step + 1e-8) * step;
   lots = MathMin(maxLot, lots);
   if(lots < minLot) return 0; // never round risk upward to broker minimum
   int digits = 2;
   if(step < 0.01) digits = 3;
   if(step < 0.001) digits = 4;
   return NormalizeDouble(lots, digits);
}

double LotsForRisk(double stopDistance) {
   double tickValue = MarketInfo(Symbol(), MODE_TICKVALUE);
   double tickSize = MarketInfo(Symbol(), MODE_TICKSIZE);
   if(stopDistance <= 0 || tickValue <= 0 || tickSize <= 0) return 0;
   double riskMoney = AccountEquity() * RiskPercent / 100.0;
   double riskPerLot = (stopDistance / tickSize) * tickValue;
   if(riskMoney <= 0 || riskPerLot <= 0) return 0;
   return NormalizeLots(riskMoney / riskPerLot);
}

bool BuildSignal(int &direction, double &atr) {
   direction = 0;
   atr = iATR(Symbol(), SignalTimeframe, ATRPeriod, 1);
   if(atr <= 0 || FastMAPeriod < 2 || SlowMAPeriod <= FastMAPeriod) return false;
   double fast1 = iMA(Symbol(), SignalTimeframe, FastMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);
   double fast2 = iMA(Symbol(), SignalTimeframe, FastMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 2);
   double slow1 = iMA(Symbol(), SignalTimeframe, SlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);
   double slow2 = iMA(Symbol(), SignalTimeframe, SlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 2);
   if(fast2 <= slow2 && fast1 > slow1) direction = 1;
   if(fast2 >= slow2 && fast1 < slow1) direction = -1;
   return true;
}

bool StopsMeetBrokerRules(double entry, double sl, double tp) {
   double minDistance = MarketInfo(Symbol(), MODE_STOPLEVEL) * Point;
   if(minDistance < 0) return false;
   if(MathAbs(entry - sl) < minDistance || MathAbs(entry - tp) < minDistance) return false;
   return true;
}

void TryOpen(int direction, double atr) {
   if(!EnableDemoTrading || !IsTradeAllowed() || IsTradeContextBusy()) return;
   if(MarketInfo(Symbol(), MODE_SPREAD) > MaxSpreadPoints) return;
   RefreshRates();
   double entry = direction > 0 ? Ask : Bid;
   double stopDistance = MathMax(atr * ATRStopMultiplier,
                                  (MarketInfo(Symbol(), MODE_STOPLEVEL) + 2) * Point);
   double sl = direction > 0 ? entry - stopDistance : entry + stopDistance;
   double tp = direction > 0 ? entry + stopDistance * RewardRiskRatio
                             : entry - stopDistance * RewardRiskRatio;
   sl = NormalizeDouble(sl, Digits);
   tp = NormalizeDouble(tp, Digits);
   if(!StopsMeetBrokerRules(entry, sl, tp)) return;

   double lots = LotsForRisk(MathAbs(entry - sl));
   if(lots <= 0) return;
   int type = direction > 0 ? OP_BUY : OP_SELL;
   ResetLastError();
   double margin = AccountFreeMarginCheck(Symbol(), type, lots);
   if(margin <= 0 || GetLastError() == 134) return;

   // SL and TP are attached to the order. If broker rejects them, fail closed.
   int ticket = OrderSend(Symbol(), type, lots, NormalizeDouble(entry, Digits),
                          SlippagePoints, sl, tp, "ARC_SILK demo MA/ATR",
                          MagicNumber, 0, clrNONE);
   if(ticket < 0) Print("ARC_SILK: order rejected; error=", GetLastError());
}

int OnInit() {
   if(!AccountDemo()) {
      Print("ARC_SILK SAFETY BLOCK: this EA is demo-account only.");
      return INIT_FAILED;
   }
   if(FastMAPeriod < 2 || SlowMAPeriod <= FastMAPeriod ||
      ATRPeriod < 2 || ATRStopMultiplier <= 0 || RewardRiskRatio <= 0 ||
      RiskPercent <= 0 || RiskPercent > 0.5 ||
      MaxDailyLossPercent <= 0 || MaxDailyLossPercent > 2.0 ||
      MaxSpreadPoints <= 0) {
      Print("ARC_SILK: invalid settings; fail closed.");
      return INIT_PARAMETERS_INCORRECT;
   }
   g_lastBar = iTime(Symbol(), SignalTimeframe, 0);
   RefreshDailyGuard();
   if(!EnableDemoTrading)
      Print("ARC_SILK loaded safely: demo trading disabled. Set EnableDemoTrading=true only on a demo account.");
   return INIT_SUCCEEDED;
}

void OnTick() {
   if(!AccountDemo()) return; // fail closed if account context changes
   RefreshDailyGuard();
   if(g_dailyLocked || !EnableDemoTrading || !IsNewSignalBar()) return;
   if(CurrentPositionCount() >= 1) return; // one position per symbol/magic
   int direction = 0;
   double atr = 0;
   if(!BuildSignal(direction, atr) || direction == 0) return;
   TryOpen(direction, atr);
}
//+------------------------------------------------------------------+
