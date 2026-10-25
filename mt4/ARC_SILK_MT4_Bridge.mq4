//+------------------------------------------------------------------+
//| ARC_SILK_MT4_Bridge.mq4                                          |
//| Quote telemetry exporter for SILKOUS Forex Intelligence.          |
//| READ-ONLY: never submits, modifies, or closes trading orders.     |
//+------------------------------------------------------------------+
#property strict
#property version   "0.2.1"
#property description "ARC_SILK MT4 read-only quote telemetry exporter."

input int    ExportIntervalSeconds = 5;
input string OutputFileName = "ARC_SILK_MT4_telemetry.csv";
input bool   ExportAccountMetrics = false; // local CSV only; never sent to bridge
input bool   EnableHttpBridge = false;      // opt in only after HTTPS service is deployed
input string BridgeUrl = "";                // base URL, e.g. https://bridge.example.com
input string BridgeToken = "";              // configure locally; never commit/share
input int    HttpTimeoutMs = 5000;

datetime g_lastExport = 0;
datetime g_last_tick_utc = 0;
long g_sequence = 0;

int OnInit()
{
   if(ExportIntervalSeconds < 1 || ExportIntervalSeconds > 300 ||
      HttpTimeoutMs < 1000 || HttpTimeoutMs > 15000)
   {
      Print("ARC_SILK: Invalid interval or HTTP timeout.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   if(EnableHttpBridge)
   {
      if(StringFind(BridgeUrl, "https://") != 0 ||
         StringLen(BridgeToken) < 32)
      {
         Print("ARC_SILK: HTTP bridge requires an HTTPS base URL and a token of at least 32 characters.");
         return(INIT_PARAMETERS_INCORRECT);
      }
      Print("ARC_SILK: HTTPS quote telemetry enabled. Add the exact bridge host under MT4 Tools > Options > Expert Advisors > Allow WebRequest.");
   }

   EventSetTimer(ExportIntervalSeconds);
   Print("ARC_SILK MT4 bridge initialized in READ-ONLY mode. HTTP bridge enabled=", EnableHttpBridge);
   ExportSnapshot();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("ARC_SILK MT4 bridge stopped. This EA does not submit trades.");
}

void OnTick()
{
   // Capture real tick time. The timer must never make an old quote look fresh.
   datetime tickUtc = TimeGMT();
   if(tickUtc > 0)
      g_last_tick_utc = tickUtc;
}

void OnTimer()
{
   ExportSnapshot();
   if(EnableHttpBridge)
      PostQuoteTelemetry();
}

void ExportSnapshot()
{
   datetime now = TimeCurrent();
   if(now <= 0 || now == g_lastExport)
      return;

   RefreshRates();
   int digits = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double bid = MarketInfo(Symbol(), MODE_BID);
   double ask = MarketInfo(Symbol(), MODE_ASK);
   double point = MarketInfo(Symbol(), MODE_POINT);
   double spreadPoints = (point > 0.0 ? (ask - bid) / point : 0.0);

   if(bid <= 0.0 || ask <= 0.0 || ask < bid)
   {
      Print("ARC_SILK: Invalid/crossed quote; snapshot skipped.");
      return;
   }

   int handle = FileOpen(OutputFileName, FILE_CSV|FILE_READ|FILE_WRITE|FILE_SHARE_READ, ',');
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

   string stamp = TimeToString(now, TIME_DATE|TIME_SECONDS);
   if(ExportAccountMetrics)
      FileWrite(handle, stamp, Symbol(), DoubleToString(bid, digits),
                DoubleToString(ask, digits), DoubleToString(spreadPoints, 1),
                AccountCurrency(), DoubleToString(AccountBalance(), 2),
                DoubleToString(AccountEquity(), 2), DoubleToString(AccountFreeMargin(), 2));
   else
      FileWrite(handle, stamp, Symbol(), DoubleToString(bid, digits),
                DoubleToString(ask, digits), DoubleToString(spreadPoints, 1));

   FileClose(handle);
   g_lastExport = now;
}

string UtcIsoTimestamp(datetime value)
{
   string stamp = TimeToString(value, TIME_DATE|TIME_SECONDS);
   StringReplace(stamp, ".", "-");
   StringReplace(stamp, " ", "T");
   return(stamp + "Z");
}

void PostQuoteTelemetry()
{
   if(StringLen(BridgeUrl) == 0 || StringLen(BridgeToken) < 32)
      return;

   datetime nowUtc = TimeGMT();
   if(g_last_tick_utc <= 0 || nowUtc <= 0 ||
      nowUtc < g_last_tick_utc || nowUtc - g_last_tick_utc > 30)
   {
      Print("ARC_SILK: HTTP telemetry skipped; no recent real market tick (30-second freshness limit).");
      return;
   }

   RefreshRates();
   int digits = (int)MarketInfo(Symbol(), MODE_DIGITS);
   double bid = MarketInfo(Symbol(), MODE_BID);
   double ask = MarketInfo(Symbol(), MODE_ASK);
   double point = MarketInfo(Symbol(), MODE_POINT);
   if(bid <= 0.0 || ask <= 0.0 || ask < bid || point <= 0.0)
   {
      Print("ARC_SILK: HTTP telemetry skipped due to invalid quote.");
      return;
   }

   double spreadPoints = (ask - bid) / point;
   g_sequence++;

   // Only market quote fields are sent. Account/balance/equity data is never sent.
   // event_time is the last actual tick time, not the timer's current time.
   string payload = StringFormat(
      "{\"schema_version\":\"1\",\"event_time\":\"%s\",\"symbol\":\"%s\",\"bid\":%s,\"ask\":%s,\"spread_points\":%s,\"sequence\":%I64d}",
      UtcIsoTimestamp(g_last_tick_utc), Symbol(), DoubleToString(bid, digits),
      DoubleToString(ask, digits), DoubleToString(spreadPoints, 1), g_sequence);

   char postData[];
   int copied = StringToCharArray(payload, postData, 0, WHOLE_ARRAY, CP_UTF8);
   if(copied <= 1)
   {
      Print("ARC_SILK: Could not encode HTTP telemetry payload.");
      return;
   }
   ArrayResize(postData, copied - 1); // remove the terminating NUL byte

   char response[];
   string responseHeaders;
   string headers = "Content-Type: application/json\r\nAuthorization: Bearer " + BridgeToken + "\r\n";
   string endpoint = BridgeUrl;
   while(StringLen(endpoint) > 0 && StringSubstr(endpoint, StringLen(endpoint)-1, 1) == "/")
      endpoint = StringSubstr(endpoint, 0, StringLen(endpoint)-1);
   endpoint += "/mt4/telemetry";

   ResetLastError();
   int status = WebRequest("POST", endpoint, headers, HttpTimeoutMs,
                           postData, response, responseHeaders);
   if(status == -1)
   {
      // Never print the URL token or request headers.
      Print("ARC_SILK: HTTPS POST failed. MT4 error=", GetLastError(),
            ". Check the HTTPS host allowlist and network availability.");
      return;
   }

   if(status < 200 || status >= 300)
      Print("ARC_SILK: Bridge rejected telemetry. HTTP status=", status);
}
