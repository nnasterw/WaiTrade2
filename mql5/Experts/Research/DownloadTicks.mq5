#property strict
#property version "1.00"

// Simple EA to download tick data from broker
input string InpSymbol = "BTCUSDm";
input string InpFrom = "2024.06.01 00:00";
input string InpTo = "2026.05.31 23:59";
input string InpPrefix = "waitrade_ticks";

bool g_done = false;

void OnTick()
{
   if(g_done) return;
   g_done = true;
   
   if(!SymbolSelect(InpSymbol, true))
   {
      Print("DownloadTicks SymbolSelect failed ", InpSymbol, " err=", GetLastError());
      return;
   }
   
   datetime from_dt = StringToTime(InpFrom);
   datetime to_dt = StringToTime(InpTo);
   
   Print("DownloadTicks start ", InpSymbol, " from=", InpFrom, " to=", InpTo);
   
   int total_ticks = 0;
   int chunk_count = 0;
   
   MqlTick ticks[];
   ArraySetAsSeries(ticks, false);
   
   // Try full range first - convert datetime to ulong (ms)
   ulong from_ms = (ulong)from_dt * 1000;
   ulong to_ms = (ulong)to_dt * 1000;
   
   int copied = CopyTicksRange(InpSymbol, ticks, COPY_TICKS_ALL, from_ms, to_ms);
   
   if(copied <= 0)
   {
      Print("DownloadTicks CopyTicksRange full failed err=", GetLastError());
      
      // Try chunks of 1 month each
      datetime chunk_start = from_dt;
      while(chunk_start < to_dt)
      {
         datetime chunk_end = MathMin(chunk_start + 30 * 86400, to_dt);
         ulong chunk_from_ms = (ulong)chunk_start * 1000;
         ulong chunk_to_ms = (ulong)chunk_end * 1000;
         int n = CopyTicksRange(InpSymbol, ticks, COPY_TICKS_ALL, chunk_from_ms, chunk_to_ms);
         if(n > 0)
         {
            total_ticks += n;
            chunk_count++;
            Print("DownloadTicks chunk [", TimeToString(chunk_start), " - ", TimeToString(chunk_end), "] got=", n);
         }
         else
         {
            Print("DownloadTicks chunk failed [", TimeToString(chunk_start), " - ", TimeToString(chunk_end), "] err=", GetLastError());
         }
         chunk_start = chunk_end + 1;
      }
   }
   else
   {
      total_ticks = copied;
      chunk_count = 1;
      Print("DownloadTicks full range got=", copied);
   }
   
   Print("DownloadTicks total: ", total_ticks, " ticks in ", chunk_count, " chunks");
}
