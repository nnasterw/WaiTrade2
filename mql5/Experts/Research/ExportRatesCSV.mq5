#property strict
#property version "1.00"

input string InpExportSymbol = "XAUUSDm";
input string InpFrom = "2024.01.01 00:00";
input string InpTo = "2026.06.18 23:59";
input string InpTFList = "1440,240,60,15,5";
input string InpPrefix = "waitrade_rates";

bool g_export_done = false;

ENUM_TIMEFRAMES MinutesToTF(int minutes)
{
   if(minutes == 1) return PERIOD_M1;
   if(minutes == 2) return PERIOD_M2;
   if(minutes == 3) return PERIOD_M3;
   if(minutes == 4) return PERIOD_M4;
   if(minutes == 5) return PERIOD_M5;
   if(minutes == 6) return PERIOD_M6;
   if(minutes == 10) return PERIOD_M10;
   if(minutes == 12) return PERIOD_M12;
   if(minutes == 15) return PERIOD_M15;
   if(minutes == 20) return PERIOD_M20;
   if(minutes == 30) return PERIOD_M30;
   if(minutes == 60) return PERIOD_H1;
   if(minutes == 120) return PERIOD_H2;
   if(minutes == 180) return PERIOD_H3;
   if(minutes == 240) return PERIOD_H4;
   if(minutes == 360) return PERIOD_H6;
   if(minutes == 480) return PERIOD_H8;
   if(minutes == 720) return PERIOD_H12;
   if(minutes == 1440) return PERIOD_D1;
   if(minutes == 10080) return PERIOD_W1;
   if(minutes == 43200) return PERIOD_MN1;
   return PERIOD_CURRENT;
}

string TFName(int minutes)
{
   if(minutes == 1440) return "D1";
   if(minutes == 240) return "H4";
   if(minutes == 60) return "H1";
   if(minutes == 15) return "M15";
   if(minutes == 5) return "M5";
   if(minutes == 1) return "M1";
   return IntegerToString(minutes);
}

void ExportOneTF(const string symbol, const int minutes, const datetime from_time, const datetime to_time)
{
   ENUM_TIMEFRAMES tf = MinutesToTF(minutes);
   if(tf == PERIOD_CURRENT)
   {
      Print("ExportRatesCSV skip unsupported tf minutes=", minutes);
      return;
   }

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int copied = -1;
   for(int attempt = 0; attempt < 5; attempt++)
   {
      ResetLastError();
      copied = CopyRates(symbol, tf, from_time, to_time, rates);
      if(copied > 0)
         break;
      Bars(symbol, tf);
      Sleep(500);
   }
   if(copied <= 0)
   {
      Print("ExportRatesCSV CopyRates failed symbol=", symbol, " tf=", TFName(minutes), " err=", GetLastError());
      return;
   }

   string filename = InpPrefix + "_" + symbol + "_" + TFName(minutes) + ".csv";
   int handle = FileOpen(filename, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("ExportRatesCSV FileOpen failed file=", filename, " err=", GetLastError());
      return;
   }

   FileWrite(handle, "time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume");
   for(int i = 0; i < copied; i++)
   {
      FileWrite(
         handle,
         TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
         DoubleToString(rates[i].open, _Digits),
         DoubleToString(rates[i].high, _Digits),
         DoubleToString(rates[i].low, _Digits),
         DoubleToString(rates[i].close, _Digits),
         (long)rates[i].tick_volume,
         (int)rates[i].spread,
         (long)rates[i].real_volume
      );
   }
   FileClose(handle);
   Print("ExportRatesCSV wrote ", filename, " bars=", copied);
}

int OnInit()
{
   datetime from_time = StringToTime(InpFrom);
   datetime to_time = StringToTime(InpTo);
   if(from_time <= 0 || to_time <= 0 || to_time <= from_time)
   {
      Print("ExportRatesCSV invalid date range from=", InpFrom, " to=", InpTo);
      return INIT_FAILED;
   }

   string symbol = (InpExportSymbol == "" ? _Symbol : InpExportSymbol);
   SymbolSelect(symbol, true);
   Print("ExportRatesCSV ready symbol=", symbol, " from=", InpFrom, " to=", InpTo, " tf=", InpTFList);
   return INIT_SUCCEEDED;
}

void RunExport()
{
   if(g_export_done)
      return;
   g_export_done = true;

   string symbol = (InpExportSymbol == "" ? _Symbol : InpExportSymbol);
   datetime from_time = StringToTime(InpFrom);
   datetime to_time = StringToTime(InpTo);
   string parts[];
   int n = StringSplit(InpTFList, ',', parts);
   for(int i = 0; i < n; i++)
   {
      int minutes = (int)StringToInteger(parts[i]);
      ExportOneTF(symbol, minutes, from_time, to_time);
   }
}

void OnTick()
{
}

void OnDeinit(const int reason)
{
   RunExport();
}
