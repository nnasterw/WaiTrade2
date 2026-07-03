#property strict

input string InpSymbol = "BTCUSDm";
input string InpPeriodsCsv = "5";
input string InpTemplatesCsv = "";
input int InpSetupDelaySec = 5;

static datetime g_start_time = 0;
static bool g_setup_done = false;

ENUM_TIMEFRAMES PeriodFromMinutes(const int minutes)
{
   switch(minutes)
   {
      case 1: return PERIOD_M1;
      case 2: return PERIOD_M2;
      case 3: return PERIOD_M3;
      case 4: return PERIOD_M4;
      case 5: return PERIOD_M5;
      case 6: return PERIOD_M6;
      case 10: return PERIOD_M10;
      case 12: return PERIOD_M12;
      case 15: return PERIOD_M15;
      case 20: return PERIOD_M20;
      case 30: return PERIOD_M30;
      case 60: return PERIOD_H1;
      case 120: return PERIOD_H2;
      case 180: return PERIOD_H3;
      case 240: return PERIOD_H4;
      case 360: return PERIOD_H6;
      case 480: return PERIOD_H8;
      case 720: return PERIOD_H12;
      case 1440: return PERIOD_D1;
      default:
         Print("PORTFOLIO_SETUP event=bad_period minutes=", minutes, " fallback=M5");
         return PERIOD_M5;
   }
}

int OnInit()
{
   g_start_time = TimeCurrent();
   EventSetTimer(1);
   Print("PORTFOLIO_SETUP event=init symbol=", InpSymbol,
         " delay=", InpSetupDelaySec,
         " periods=", InpPeriodsCsv,
         " templates=", InpTemplatesCsv);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("PORTFOLIO_SETUP event=deinit reason=", reason);
}

void OnTimer()
{
   if(g_setup_done)
      return;

   if(TimeCurrent() - g_start_time < InpSetupDelaySec)
      return;

   g_setup_done = true;
   EventKillTimer();
   SetupCharts();
   ExpertRemove();
}

void OnTick()
{
}

void SetupCharts()
{
   string templates[];
   string periods[];
   int template_count = StringSplit(InpTemplatesCsv, ',', templates);
   int period_count = StringSplit(InpPeriodsCsv, ',', periods);

   Print("PORTFOLIO_SETUP event=start symbol=", InpSymbol,
         " template_count=", template_count,
         " period_count=", period_count);

   if(template_count <= 0 || period_count <= 0 || template_count != period_count)
   {
      Print("PORTFOLIO_SETUP event=config_error template_count=", template_count,
            " period_count=", period_count);
      return;
   }

   for(int i = 0; i < template_count; i++)
   {
      int minutes = (int)StringToInteger(periods[i]);
      ENUM_TIMEFRAMES period = PeriodFromMinutes(minutes);

      ResetLastError();
      long chart_id = ChartOpen(InpSymbol, period);
      int open_error = GetLastError();
      if(chart_id <= 0)
      {
         Print("PORTFOLIO_SETUP event=open_failed index=", i + 1,
               " period=", minutes,
               " template=", templates[i],
               " error=", open_error);
         continue;
      }

      Sleep(500);
      ResetLastError();
      bool applied = ChartApplyTemplate(chart_id, templates[i]);
      int apply_error = GetLastError();
      Print("PORTFOLIO_SETUP event=chart index=", i + 1,
            " chart=", chart_id,
            " period=", minutes,
            " template=", templates[i],
            " applied=", (applied ? "true" : "false"),
            " error=", apply_error);
   }

   Print("PORTFOLIO_SETUP event=done");
}
