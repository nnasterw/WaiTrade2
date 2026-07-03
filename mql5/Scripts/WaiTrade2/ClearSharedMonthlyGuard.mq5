#property script_show_inputs
#property strict

input string InpSharedMonthlyGuardKey = "";

void OnStart()
{
   if(StringLen(InpSharedMonthlyGuardKey) == 0)
   {
      Print("ClearSharedMonthlyGuard: InpSharedMonthlyGuardKey is empty");
      return;
   }

   string prefix = "WT2_MONTH_" + InpSharedMonthlyGuardKey + "_";
   int removed = GlobalVariablesDeleteAll(prefix);
   Print("ClearSharedMonthlyGuard: prefix=", prefix, " removed=", removed);
}
