//+------------------------------------------------------------------+
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

    // R5: M15逆势+在M15 OB内→BLOCK (M15是M1的自然上级,不过度跨级)
    if(InpMTFEnableR5BlockCounterH1 && !align.aligned_m15&&g_mtf_ctx.trend_m15.direction!=0
       &&(align.inside_m15_buy_ob||align.inside_m15_sell_ob))
    {v.verdict=MTF_BLOCK;v.effective_mult=0.0;v.reason="R5:M15 counter inside M15 OB BLOCK";return;}

    // R4v3: M15逆势+压力极端, 趋势强→REDUCE(回调入场), 趋势弱→BLOCK(震荡噪音)
    if(InpMTFEnableR4BlockCounterM15AtZone && !align.aligned_m15&&align.pressure_extreme)
    {
        if(g_mtf_ctx.trend_m15.strength>0.35)
        {v.verdict=MTF_REDUCE_30;v.effective_mult=0.3;v.reason="R4v3:M15 counter+pressure strong trend REDUCE";return;}
        else
        {v.verdict=MTF_BLOCK;v.effective_mult=0.0;v.reason="R4v3:M15 counter+pressure weak trend BLOCK";return;}
    }

    if(!align.aligned_h4&&g_mtf_ctx.trend_h4.direction!=0&&(align.inside_h4_buy_ob||align.inside_h4_sell_ob))
    {v.verdict=MTF_REDUCE_30;v.effective_mult=0.3;v.reason="H4 counter inside H4 OB REDUCE 0.3";return;}

    if(align.is_counter_trend&&align.pressure_extreme)
    {v.verdict=MTF_REDUCE_30;v.effective_mult=0.3;v.reason="H1 counter+pressure REDUCE 0.3";return;}

    int run=(g_mtf_ctx.run_active_dir==OB_BUY)?g_mtf_ctx.run_buy:g_mtf_ctx.run_sell;
    if(InpMTFEnableR1bReduceDeepRun && run>4&&align.pressure_extreme)
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
