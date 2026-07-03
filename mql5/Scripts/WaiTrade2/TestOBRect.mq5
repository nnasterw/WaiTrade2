#property copyright "Test"
#property version "1.00"
#property script_show_inputs

input int InpNum = 5; // 创建几个测试矩形

void OnStart()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double mid = (bid + ask) / 2.0;
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double range = 200 * point; // 2美元区间

   Print("=== TestOBRect: bid=", bid, " ask=", ask, " point=", point, " ===");

   for(int i = 0; i < InpNum; i++)
   {
      datetime t1 = TimeCurrent() - (InpNum - i) * 300; // 每5分钟一个
      datetime t2 = TimeCurrent() + 300;

      double hi = mid + range * (i + 1) / InpNum;
      double lo = mid - range * (i + 1) / InpNum;

      string nm = "TEST_RECT_" + IntegerToString(i);
      ObjectDelete(0, nm);

      bool ok = ObjectCreate(0, nm, OBJ_RECTANGLE, 0, t1, hi, t2, lo);
      int err = GetLastError();

      Print("  [", i, "] ObjectCreate=", ok, " err=", err, " name=", nm,
            " t1=", TimeToString(t1), " t2=", TimeToString(t2),
            " hi=", DoubleToString(hi, _Digits), " lo=", DoubleToString(lo, _Digits));

      if(ok)
      {
         ObjectSetInteger(0, nm, OBJPROP_COLOR, (i % 2 == 0) ? clrBlue : clrRed);
         ObjectSetInteger(0, nm, OBJPROP_STYLE, STYLE_DASH);
         ObjectSetInteger(0, nm, OBJPROP_WIDTH, 3);
         ObjectSetInteger(0, nm, OBJPROP_BACK, false);
         ObjectSetInteger(0, nm, OBJPROP_FILL, true);
         ObjectSetInteger(0, nm, OBJPROP_HIDDEN, false);
         ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, true);
         ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, true);
      }
   }

   ChartRedraw(0);
   Print("=== TestOBRect: done, ", InpNum, " rectangles created. Check chart. ===");
}
