#!/usr/bin/env python3
"""Create MTFContext.mqh and modify Config.mqh, WaiTrade_OB.mq5, SignalEngine.mqh"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

# ====== 1. Create MTFContext.mqh ======
MTF_CONTENT = r"""//+------------------------------------------------------------------+
//| MTFContext.mqh - MTF multi-TF OB framework v3                       |
//+------------------------------------------------------------------+
#property copyright "WaiTrade2"
#property strict
#ifndef WAITRADE2_MTFCONTEXT_MQH
#define WAITRADE2_MTFCONTEXT_MQH

#include <WaiTrade2/Types.mqh>
#include <WaiTrade2/Config.mqh>
#include <WaiTrade2/MathUtils.mqh>

#define MTF_MAX_OB_ZONES 5

enum ENUM_PRESSURE_ZONE { PRESSURE_NONE=0, PRESSURE_LOW=1, PRESSURE_MID=2, PRESSURE_HIGH=3 };
enum ENUM_MTF_VERDICT   { MTF_BLOCK=0, MTF_REDUCE_50=50, MTF_REDUCE_30=30, MTF_ALLOW=100 };

struct MTFOBZone     { double high,low; int direction,age_bars; datetime created; };
struct MTFOBStore    { MTFOBZone zones[MTF_MAX_OB_ZONES]; int count; };
struct MTFTrendInfo  { int direction; double strength,ma_fast,ma_slow,atr; };
struct MTFAlignment  {
    bool aligned_m15,aligned_h1,aligned_h4;
    bool inside_m15_buy_ob,inside_m15_sell_ob,inside_h1_buy_ob,inside_h1_sell_ob;
    bool inside_h4_buy_ob,inside_h4_sell_ob;
    bool pressure_extreme,high_zone_buy,low_zone_sell,is_counter_trend;
    int  conflict_count;
};
struct MTFVerdict    { ENUM_MTF_VERDICT verdict; double effective_mult; int conflict_count; string reason; };
struct MTFContext    {
    bool initialized;
    MTFTrendInfo trend_m15,trend_h1,trend_h4;
    MTFOBStore   ob_m15,ob_h1,ob_h4;
    ENUM_PRESSURE_ZONE pressure_zone;
    double pressure_range_high,pressure_range_low;
    int  run_buy,run_sell,run_active_dir;
    datetime run_last_time;
    int  last_update_bar_m15,last_update_bar_h1,last_update_bar_h4,last_update_bar_pressure;
};

MTFContext g_mtf_ctx;

bool IsInsideOB(double p,const MTFOBZone &z){return p>=z.low-0.01 && p<=z.high+0.01;}

ENUM_PRESSURE_ZONE CalcPressureZone(string sym,int lb,double &rh,double &rl)
{
    MqlRates rt[];int n=CopyRates(sym,GetWorkTF(),0,lb+1,rt);
    if(n<5){rh=0;rl=0;return PRESSURE_NONE;}
    double h=rt[1].high,l=rt[1].low;
    for(int i=2;i<n;i++){if(rt[i].high>h)h=rt[i].high;if(rt[i].low<l)l=rt[i].low;}
    rh=h;rl=l;double bid=SymbolInfoDouble(sym,SYMBOL_BID);
    if(bid<=0)return PRESSURE_NONE;
    double rng=h-l;if(rng<=0)return PRESSURE_MID;
    double pct=(bid-l)/rng*100.0;
    if(pct>=70.0)return PRESSURE_HIGH;
    if(pct<=30.0)return PRESSURE_LOW;
    return PRESSURE_MID;
}

MTFTrendInfo DetectTrendOnTF(string sym,ENUM_TIMEFRAMES tf,int lb,int mf,int ms)
{
    MTFTrendInfo info;ZeroMemory(info);
    MqlRates rt[];int n=CopyRates(sym,tf,0,lb+ms+1,rt);
    if(n<ms+2)return info;
    double sf=0,ss=0;
    for(int i=1;i<=mf;i++)sf+=rt[i].close;
    for(int i=1;i<=ms;i++)ss+=rt[i].close;
    info.ma_fast=sf/mf;info.ma_slow=ss/ms;
    double pf=0,ps=0;
    for(int i=2;i<=mf+1;i++)pf+=rt[i].close;
    for(int i=2;i<=ms+1;i++)ps+=rt[i].close;
    pf/=mf;ps/=ms;
    bool nu=(info.ma_fast>info.ma_slow),pu=(pf>ps);
    if(nu&&!pu)info.direction=1;
    else if(!nu&&pu)info.direction=-1;
    else if(nu)info.direction=1;else info.direction=-1;
    double atr=0;
    for(int i=1;i<=lb&&i<n;i++)atr+=MathAbs(rt[i].high-rt[i].low);
    info.atr=atr/(double)lb;
    double rng=info.atr>0?info.atr:1.0;
    info.strength=MathAbs(info.ma_fast-info.ma_slow)/rng;
    if(info.strength>1.0)info.strength=1.0;
    return info;
}

void DetectOBOnTF(string sym,ENUM_TIMEFRAMES tf,int depth,MTFOBStore &store)
{
    store.count=0;MqlRates rt[];int n=CopyRates(sym,tf,0,depth+3,rt);
    if(n<5)return;
    for(int i=2;i<n-1&&store.count<MTF_MAX_OB_ZONES;i++)
    {
        double body=MathAbs(rt[i].close-rt[i].open);
        double range=rt[i].high-rt[i].low;
        if(range<=0||body/range<0.5)continue;
        bool is_buy=(rt[i].close>rt[i].open);
        bool ll=(rt[i-1].high<rt[i].high&&rt[i-2].high<rt[i].high);
        bool lh=(rt[i-1].low>rt[i].low&&rt[i-2].low>rt[i].low);
        if(is_buy&&ll)
        {
            store.zones[store.count].high=rt[i].high;
            store.zones[store.count].low=rt[i].low;
            store.zones[store.count].direction=OB_BUY;
            store.zones[store.count].created=rt[i].time;
            store.count++;
        }
        else if(!is_buy&&lh)
        {
            store.zones[store.count].high=rt[i].high;
            store.zones[store.count].low=rt[i].low;
            store.zones[store.count].direction=OB_SELL;
            store.zones[store.count].created=rt[i].time;
            store.count++;
        }
    }
}

void UpdateMTFContext(string sym,MTFContext &ctx)
{
    if(!ctx.initialized){ZeroMemory(ctx);ctx.initialized=true;return;}
    int b15=Bars(sym,PERIOD_M15),b60=Bars(sym,PERIOD_H1),b240=Bars(sym,PERIOD_H4);
    int wf=Bars(sym,GetWorkTF());
    if(b15!=ctx.last_update_bar_m15){
        ctx.trend_m15=DetectTrendOnTF(sym,PERIOD_M15,24,8,21);
        DetectOBOnTF(sym,PERIOD_M15,100,ctx.ob_m15);
        ctx.last_update_bar_m15=b15;
    }
    if(b60!=ctx.last_update_bar_h1){
        ctx.trend_h1=DetectTrendOnTF(sym,PERIOD_H1,24,8,21);
        DetectOBOnTF(sym,PERIOD_H1,100,ctx.ob_h1);
        ctx.last_update_bar_h1=b60;
    }
    if(b240!=ctx.last_update_bar_h4){
        ctx.trend_h4=DetectTrendOnTF(sym,PERIOD_H4,24,8,21);
        DetectOBOnTF(sym,PERIOD_H4,100,ctx.ob_h4);
        ctx.last_update_bar_h4=b240;
    }
    if(wf!=ctx.last_update_bar_pressure){
        ctx.pressure_zone=CalcPressureZone(sym,24,ctx.pressure_range_high,ctx.pressure_range_low);
        ctx.last_update_bar_pressure=wf;
    }
}

void RecordEntryDirection(MTFContext &ctx,int dir)
{
    if(dir==OB_BUY){ctx.run_buy++;ctx.run_sell=0;ctx.run_active_dir=OB_BUY;}
    else if(dir==OB_SELL){ctx.run_sell++;ctx.run_buy=0;ctx.run_active_dir=OB_SELL;}
    ctx.run_last_time=TimeCurrent();
}

bool ClassifyEntry(const MTFContext &ctx,int dir,double ep,MTFAlignment &align)
{
    ZeroMemory(align);
    align.aligned_m15=(ctx.trend_m15.direction!=0&&ctx.trend_m15.direction==dir);
    align.aligned_h1 =(ctx.trend_h1.direction!=0&&ctx.trend_h1.direction==dir);
    align.aligned_h4 =(ctx.trend_h4.direction!=0&&ctx.trend_h4.direction==dir);
    for(int i=0;i<ctx.ob_m15.count;i++)
        if(IsInsideOB(ep,ctx.ob_m15.zones[i])){
            if(ctx.ob_m15.zones[i].direction==OB_BUY)align.inside_m15_buy_ob=true;
            else align.inside_m15_sell_ob=true;
        }
    for(int i=0;i<ctx.ob_h1.count;i++)
        if(IsInsideOB(ep,ctx.ob_h1.zones[i])){
            if(ctx.ob_h1.zones[i].direction==OB_BUY)align.inside_h1_buy_ob=true;
            else align.inside_h1_sell_ob=true;
        }
    for(int i=0;i<ctx.ob_h4.count;i++)
        if(IsInsideOB(ep,ctx.ob_h4.zones[i])){
            if(ctx.ob_h4.zones[i].direction==OB_BUY)align.inside_h4_buy_ob=true;
            else align.inside_h4_sell_ob=true;
        }
    align.is_counter_trend=(!align.aligned_h1&&ctx.trend_h1.direction!=0);
    if(ctx.pressure_zone==PRESSURE_HIGH&&dir==OB_BUY)align.high_zone_buy=true;
    if(ctx.pressure_zone==PRESSURE_LOW&&dir==OB_SELL)align.low_zone_sell=true;
    align.pressure_extreme=(ctx.pressure_zone==PRESSURE_HIGH||ctx.pressure_zone==PRESSURE_LOW);
    align.conflict_count=0;
    if(align.is_counter_trend)align.conflict_count++;
    if(align.pressure_extreme)align.conflict_count++;
    if(align.inside_h1_buy_ob&&dir==OB_SELL)align.conflict_count++;
    if(align.inside_h1_sell_ob&&dir==OB_BUY)align.conflict_count++;
    if(align.inside_h4_buy_ob&&dir==OB_SELL)align.conflict_count++;
    if(align.inside_h4_sell_ob&&dir==OB_BUY)align.conflict_count++;
    return true;
}

void ApplyMTFRules(const MTFAlignment &align,MTFVerdict &v)
{
    ZeroMemory(v);v.verdict=MTF_ALLOW;v.effective_mult=1.0;v.conflict_count=align.conflict_count;

    if(align.is_counter_trend&&(align.inside_h1_buy_ob||align.inside_h1_sell_ob))
    {v.verdict=MTF_BLOCK;v.effective_mult=0.0;v.reason="R5:H1 counter inside H1 OB BLOCK";return;}

    if(!align.aligned_m15&&align.pressure_extreme)
    {v.verdict=MTF_BLOCK;v.effective_mult=0.0;v.reason="R4:M15 counter at pressure BLOCK";return;}

    if(!align.aligned_h4&&g_mtf_ctx.trend_h4.direction!=0&&(align.inside_h4_buy_ob||align.inside_h4_sell_ob))
    {v.verdict=MTF_REDUCE_30;v.effective_mult=0.3;v.reason="H4 counter inside H4 OB REDUCE 0.3";return;}

    if(align.is_counter_trend&&align.pressure_extreme)
    {v.verdict=MTF_REDUCE_30;v.effective_mult=0.3;v.reason="H1 counter+pressure REDUCE 0.3";return;}

    int run=(g_mtf_ctx.run_active_dir==OB_BUY)?g_mtf_ctx.run_buy:g_mtf_ctx.run_sell;
    if(run>4&&align.pressure_extreme)
    {v.verdict=MTF_REDUCE_50;v.effective_mult=0.5;v.reason="R1b:deep run+pressure REDUCE 0.5";return;}

    if(!align.aligned_m15&&g_mtf_ctx.trend_m15.direction!=0)
    {v.verdict=MTF_REDUCE_50;v.effective_mult=0.5;v.reason="M15 counter REDUCE 0.5";}

    if(align.conflict_count>=2&&v.verdict==MTF_ALLOW)
    {v.verdict=MTF_REDUCE_50;v.effective_mult=0.5;v.reason="2+ conflicts REDUCE 0.5";}
}

double ApplyMTFVerdict(const MTFVerdict &v,double pm)
{
    if(v.verdict==MTF_BLOCK)return -1.0;
    return pm*v.effective_mult;
}

double AdjustPosMultByMTF(MTFContext &ctx,string sym,int dir,double ep,double pm)
{
    if(!InpEnableMTF)return pm;
    MTFAlignment align;ClassifyEntry(ctx,dir,ep,align);
    MTFVerdict v;ApplyMTFRules(align,v);
    double r=ApplyMTFVerdict(v,pm);
    if(InpEnableEntryDebug&&v.verdict!=MTF_ALLOW)
        Print("MTF_DIAG dir=",dir," v=",v.reason," cf=",align.conflict_count," in=",(r<0?"BLOCK":DoubleToString(r,2)));
    return r;
}
#endif
"""

mtf_path = ROOT / 'mql5' / 'Include' / 'WaiTrade2' / 'MTFContext.mqh'
mtf_path.write_text(MTF_CONTENT, encoding='utf-8')
print(f"Created: {mtf_path} ({len(MTF_CONTENT)} bytes)")

# ====== 2. Add Config.mqh parameters ======
config_path = ROOT / 'mql5' / 'Include' / 'WaiTrade2' / 'Config.mqh'
config = config_path.read_text(encoding='utf-8')

mtf_params = """
// ---- MTF multi-TF OB framework v3 ----
input bool   InpEnableMTF                       = false;    // MTF总开关(多周期OB检测+规则引擎)
input int    InpMTFOBScanDepth                  = 100;      // MTF OB扫描深度(每TF bars)
input int    InpMTFLookbackBars                 = 24;       // MTF趋势/压力区回溯bars
input int    InpMTFTrendFast                    = 8;        // MTF趋势判别快线周期
input int    InpMTFTrendSlow                    = 21;       // MTF趋势判别慢线周期
input int    InpMTFMaxConsecutiveDir            = 4;        // 最大连续同向入场(超后降权)
input double InpMTFPressureZoneHighPct          = 70.0;     // 压力区HIGH阈值(%)
input double InpMTFPressureZoneLowPct           = 30.0;     // 压力区LOW阈值(%)
input bool   InpMTFEnableR5BlockCounterH1       = true;     // R5: H1逆势+在H1 OB内->BLOCK
input bool   InpMTFEnableR4BlockCounterM15AtZone= true;     // R4: M15逆势+压力极端->BLOCK
input bool   InpMTFEnableR1bReduceDeepRun       = true;     // R1b: 同向连跑+压力极端->REDUCE
"""

# Insert before function definitions
insert_point = config.find('double GetEffectiveEntryDepthPct()')
if insert_point > 0:
    config = config[:insert_point] + mtf_params + '\n' + config[insert_point:]
    config_path.write_text(config, encoding='utf-8')
    print(f"Modified: {config_path} (+{len(mtf_params)} bytes)")
else:
    print("ERROR: Could not find insertion point in Config.mqh")

# ====== 3. Add include to WaiTrade_OB.mq5 ======
ea_path = ROOT / 'mql5' / 'Experts' / 'WaiTrade2' / 'WaiTrade_OB.mq5'
ea = ea_path.read_text(encoding='utf-8')

# Add include after BarTracker
ea = ea.replace(
    '#include <WaiTrade2/BarTracker.mqh>',
    '#include <WaiTrade2/BarTracker.mqh>\n#include <WaiTrade2/MTFContext.mqh>'
)

# Add UpdateMTFContext after market_state detection (DetectMarketState block ending)
ea = ea.replace(
    'g_state.atr_m15 = CalcATR(rates_m15, m15_count, InpATRPeriod);',
    'g_state.atr_m15 = CalcATR(rates_m15, m15_count, InpATRPeriod);\n            if(InpEnableMTF) UpdateMTFContext(symbol, g_mtf_ctx);'
)

# Add RecordEntryDirection after ExecuteSignal success (in ExecuteChannelConfirmed)
# The pattern: after "state.pos_count++;" in the confirmed execution path
ea = ea.replace(
    'state.pos_count++;\n',
    'state.pos_count++;\n                if(InpEnableMTF) RecordEntryDirection(g_mtf_ctx, confirmed[i].direction);\n',
    1  # Only first occurrence (ExecuteChannelConfirmed)
)

ea_path.write_text(ea, encoding='utf-8')
print(f"Modified: {ea_path}")

# ====== 4. Add MTF check to SignalEngine.mqh ======
sig_path = ROOT / 'mql5' / 'Include' / 'WaiTrade2' / 'SignalEngine.mqh'
sig = sig_path.read_text(encoding='utf-8')

# Add include at top
sig = sig.replace(
    '#include <WaiTrade2/MathUtils.mqh>',
    '#include <WaiTrade2/MathUtils.mqh>\n#include <WaiTrade2/MTFContext.mqh>'
)

# Add MTF check in FinalizeEntryEngineSignal - after pos_mult cap, before continuation filter
# Find the pattern: after ApplyPositionMultiplierCap or similar pos_mult finalization
# Look for "PassContinuationAgeFilter" which is after pos_mult chain
sig = sig.replace(
    'if(!PassContinuationAgeFilter(zone, state, signal.deep_entry))',
    '   if(InpEnableMTF)\n   {\n      double mtf_pm = AdjustPosMultByMTF(g_mtf_ctx, symbol, signal.direction,\n         (signal.direction == OB_BUY) ? signal.entry_price : signal.entry_price, pos_mult);\n      if(mtf_pm < 0) { if(InpEnableEntryDebug) Print("MTF_BLOCK dir=",signal.direction); return false; }\n      pos_mult = mtf_pm;\n   }\n   if(!PassContinuationAgeFilter(zone, state, signal.deep_entry))'
)

sig_path.write_text(sig, encoding='utf-8')
print(f"Modified: {sig_path}")

# ====== 5. Add FLAT_MAP to yaml_to_set.py ======
yts_path = ROOT / 'scripts' / 'yaml_to_set.py'
yts = yts_path.read_text(encoding='utf-8')

mtf_flatmap = '''
    # MTF multi-TF framework v3
    "enable_mtf": "InpEnableMTF",
    "mtf_ob_scan_depth": "InpMTFOBScanDepth",
    "mtf_lookback_bars": "InpMTFLookbackBars",
    "mtf_trend_fast": "InpMTFTrendFast",
    "mtf_trend_slow": "InpMTFTrendSlow",
    "mtf_max_consecutive_dir": "InpMTFMaxConsecutiveDir",
    "mtf_pressure_high_pct": "InpMTFPressureZoneHighPct",
    "mtf_pressure_low_pct": "InpMTFPressureZoneLowPct",
    "mtf_enable_r5_block_counter_h1": "InpMTFEnableR5BlockCounterH1",
    "mtf_enable_r4_block_counter_m15_zone": "InpMTFEnableR4BlockCounterM15AtZone",
    "mtf_enable_r1b_reduce_deep_run": "InpMTFEnableR1bReduceDeepRun",
'''

# Find the last FLAT_MAP entry
last_map = yts.rfind('"enable_entry_debug":')
if last_map > 0:
    end_of_line = yts.find('\n', last_map)
    yts = yts[:end_of_line+1] + mtf_flatmap + yts[end_of_line+1:]
    yts_path.write_text(yts, encoding='utf-8')
    print(f"Modified: {yts_path}")
else:
    print("ERROR: Could not find FLAT_MAP insertion point")

# ====== 6. Add defaults to strategies.yaml ======
yaml_path = ROOT / 'config' / 'strategies.yaml'
yaml_content = yaml_path.read_text(encoding='utf-8')

mtf_defaults = '''
  # === MTF multi-TF framework v3 ===
  enable_mtf: false
  mtf_ob_scan_depth: 100
  mtf_lookback_bars: 24
  mtf_trend_fast: 8
  mtf_trend_slow: 21
  mtf_max_consecutive_dir: 4
  mtf_pressure_high_pct: 70.0
  mtf_pressure_low_pct: 30.0
  mtf_enable_r5_block_counter_h1: true
  mtf_enable_r4_block_counter_m15_zone: true
  mtf_enable_r1b_reduce_deep_run: true
'''

# Insert after "structure_break_atr" in defaults
insert_at = yaml_content.find('structure_break_atr:')
if insert_at > 0:
    end_of_line = yaml_content.find('\n', insert_at)
    yaml_content = yaml_content[:end_of_line+1] + mtf_defaults + yaml_content[end_of_line+1:]
    yaml_path.write_text(yaml_content, encoding='utf-8')
    print(f"Modified: {yaml_path}")
else:
    print("ERROR: Could not find defaults insertion point")

print("\n=== All MTF framework files created/modified ===")
print("Next step: Compile WaiTrade_OB.mq5 in MetaEditor (0 errors, 0 warnings)")
print("Then: python scripts/yaml_to_set.py --all")
print("Then: Phase 1 verification backtest")
