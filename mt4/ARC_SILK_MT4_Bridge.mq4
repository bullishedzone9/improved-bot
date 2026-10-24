//+------------------------------------------------------------------+
//| ARC_SILK_MT4_Bridge.mq4                                          |
//| Telemetry-only foundation for SILKOUS Forex Intelligence.         |
//| IMPORTANT: This EA does not place, modify, or close orders.       |
//+------------------------------------------------------------------+
#property strict
#property version   "0.1.0"
#property description "ARC_SILK MT4 quote/account telemetry exporter; no trade execution."

input int    ExportIntervalSeconds = 5;
input string OutputFileName = "ARC_SILK_MT4_telemetry.csv";
input bool   ExportAccountMetrics = true;

datetime g_lastExport = 0;

// Keep the initial bridge deliberately read-only. No OrderSend,
// OrderModify, OrderClose, DLL imports, or remote network requests.

int OnInit()
{
   if(ExportIntervalSeconds < 1 || ExportIntervalSeconds > 300)
   {
      Print("ARC_SILK: ExportIntervalSeconds must be between 1 and 300.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   EventSetTimer(ExportIntervalSeconds);
   Print("ARC_SILK MT4 bridge initialized in READ-ONLY mode. Output: MQL4/Files/",
         OutputFileName);
   ExportSnapshot();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("ARC_SILK MT4 bridge stopped. No trades were submitted by this EA.");
}

void OnTick()
{
   // Timer-based export is used to keep file output frequency predictable.
}

void OnTimer()
{
   ExportSnapshot();
}

void ExportSnapshot()
{
   datetime now = TimeCurrent();
   if(now <= 0 || now == g_lastExport)
      return;

   RefreshRates();

   int handle = FileOpen(OutputFileName,
                         FILE_CSV|FILE_READ|FILE_WRITE|FILE_SHARE_READ,
                         ',');
   if(handle == INVALID_HANDLE)
   {
      Print("ARC_SILK: Cannot open telemetry file. Error=", GetLastError());
      return;
   }

   bool writeHeader = (FileSize(handle) == 0);
   FileSeek(handle, 0, SEEK_END);

   if(writeHeader)
   {
      if(ExportAccountMetrics)
         FileWrite(handle, "server_time", "symbol", "bid", "ask", "spread_points",
                   "account_currency", "balance", "equity", "free_margin");
      else
         FileWrite(handle, "server_time", "symbol", "bid", "ask", "spread_points");
   }

   int digits = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double bid = MarketInfo(Symbol(), MODE_BID);
   double ask = MarketInfo(Symbol(), MODE_ASK);
   double point = MarketInfo(Symbol(), MODE_POINT);
   double spreadPoints = (point > 0.0 ? (ask - bid) / point : 0.0);

   if(bid <= 0.0 || ask <= 0.0 || ask < bid)
   {
      FileClose(handle);
      Print("ARC_SILK: Invalid/crossed quote; snapshot skipped.");
      return;
   }

   string stamp = TimeToString(now, TIME_DATE|TIME_SECONDS);
   if(ExportAccountMetrics)
   {
      FileWrite(handle, stamp, Symbol(), DoubleToString(bid, digits),
                DoubleToString(ask, digits), DoubleToString(spreadPoints, 1),
                AccountCurrency(), DoubleToString(AccountBalance(), 2),
                DoubleToString(AccountEquity(), 2),
                DoubleToString(AccountFreeMargin(), 2));
   }
   else
   {
      FileWrite(handle, stamp, Symbol(), DoubleToString(bid, digits),
                DoubleToString(ask, digits), DoubleToString(spreadPoints, 1));
   }

   FileClose(handle);
   g_lastExport = now;
}
