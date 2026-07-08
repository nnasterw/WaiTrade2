#ifndef __WAITRADE_CONFIG_MQH__
#define __WAITRADE_CONFIG_MQH__

bool IsMonthlyDefensiveModeActive();
bool IsRuntimeDefensiveModeActive();
bool IsAdaptiveNoiseGateDefensive();    // 权益回撤>阈值 → 启用防守噪音参数
bool IsATRLowVolRegime();               // ATR当前/历史<阈值 → 低波防守体制
double CfgTickNoiseGateMinDirRatio();   // 正常/防守态tick方向一致率
double CfgTickNoiseGateMaxRangeATR();   // 正常/防守态tick振幅上限
double CfgAdaptiveBoostIn1HOB();        // 自适应1H OB加仓倍数(防守态降权)
double CfgAdaptiveDeepEntryBoost();     // 自适应深位入场加仓倍数(防守态降权)
bool   IsDoubleSweepRegime();            // 双扫体制检测: 双方向LP被扫=震荡区间

//鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
// WaiTrade2 EA 鈥?杈撳叆鍙傛暟瀹氫箟 (V96b榛樿鍊?
// 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?

// 鈹€鈹€ OB妫€娴?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpBouncePct        = 0.30;     // OB纭鍙嶅脊骞呭害(%)
input int    InpTimeoutMin       = 60;       // OB杩囨湡鏃堕棿(鍒嗛挓)
input double InpMaxEntryOffsetR  = 1.5;      // 鏈€澶у叆鍦哄亸绉?R鍊嶆暟)
input double InpEntryDepthPct    = 0.0;      // OB娣卞叆瑙﹀強姣斾緥(0=杈圭紭,0.5=涓嚎,0.67=涓笅/涓笂)
input bool   InpEntryDepthFilter = true;     // true=蹇呴』娣变綅瑙﹀強鎵嶅叆鍦?false=娣变綅浠呬綔鍔犱粨鏍囪
input string InpEntryDepthSignalTypes = "";  // 指定哪些信号族启用更深入口(空=全局)
input double InpEntryDepthRelaxMinBalance = 0.0; // 浣欓杈惧埌璇ュ€煎悗鍚敤杈冩祬EntryDepthPct(0=濮嬬粓鍚敤)
input double InpDeepEntryBoost   = 1.0;      // 娣卞叆OB鍚庡叆鍦虹殑浠撲綅鍊嶆暟(1=绂佺敤鍔犱粨)
input int    InpEntryConfirmBars = 0;        // Bounce鍚庨渶绐佺牬鏈€杩慛鏍筀绾块珮/浣?0=绂佺敤)
input int    InpBounceCloseConfirmBars = 0;  // Bounce鍚庨渶杩炵画N鏍规敹鍦∣B澶栦晶(0=绂佺敤)
input int    InpBounceCloseTF    = 1;        // Bounce鏀剁洏纭鍛ㄦ湡(鍒嗛挓,0=宸ヤ綔鍛ㄦ湡)
input double InpBounceCloseBufferPct = 0.0;  // 鏀剁洏闇€瓒婅繃OB杈圭紭鐨凮B楂樺害姣斾緥
input bool   InpBounceCloseRequireBody = false; // 鏀剁洏纭K闇€鍚屾柟鍚戝疄浣?
input double InpBounceCloseMinBodyPct = 0.0; // Closed confirmation candle min body/range pct, 0=disabled
input double InpBounceCloseWeakBodyPct = 0.0; // Confirmation body below this is weak, 0=disabled
input double InpBounceCloseWeakBodyMult = 1.0; // Weak confirmation position multiplier, <=0 blocks
input double InpDefensiveConfirmMaxBalance = 0.0; // Balance <= this enables defensive OB close/VSL overrides
input double InpDefensiveConfirmMinPrice = 0.0; // Defensive mode requires current price >= this, 0=disabled
input double InpDefensiveConfirmMaxPrice = 0.0; // Defensive mode requires current price <= this, 0=disabled
input int    InpDefensiveBounceCloseConfirmBars = 0; // Defensive OB close confirm bars
input double InpDefensiveBounceCloseBufferPct = 0.0; // Defensive OB close buffer as OB height pct
input bool   InpDefensiveBounceCloseRequireBody = false; // Defensive OB close must be directional body
input double InpDefensiveBounceCloseMinBodyPct = 0.0; // Defensive confirmation candle min body/range pct
input double InpDefensiveBounceCloseWeakBodyPct = 0.0; // Defensive weak body threshold
input double InpDefensiveBounceCloseWeakBodyMult = 1.0; // Defensive weak body multiplier
input double InpDefensiveBounceSweetMinPct = 0.0; // Defensive OB reaction depth min pct, 0=disabled
input double InpDefensiveBounceSweetMaxPct = 0.0; // Defensive OB reaction depth max pct, 0=disabled
input double InpDefensiveOutsideBounceSweetMult = 1.0; // Defensive outside reaction-depth multiplier
input int    InpDefensiveMaxEntriesPerOB = 0; // Defensive max entries per OB, 0=use normal
input int    InpDefensiveOBReentryCooldownMin = 0; // Defensive same-OB cooldown, 0=use normal
input double InpDefensiveShallowConfirmPosMin = -999.0; // Defensive shallow confirm threshold
input double InpDefensiveShallowConfirmPosMult = 1.0; // Defensive shallow confirm multiplier
input double InpRuntimeDefensiveDrawdownPct = 0.0; // EA启动后从峰值回撤达到该百分比启用防守(0=禁用)
input int    InpRuntimeDefensiveMinTrades = 0; // 运行期防守至少交易笔数
input double InpRuntimeDefensiveMaxBalance = 0.0; // 当前余额不高于该值时才启用运行期防守(0=不限制)
input double InpRuntimeDefensivePosMult = 1.0; // 运行期防守仓位倍数(<=0过滤)
input bool   InpEnableConfirmPullback = false; // Bounce纭鍚庣瓑寰呯煭鍥炶俯鍏ュ満
input double InpConfirmPullbackPct = 0.50;   // 鍥炶俯姣斾緥: 瑙︾偣鍒扮‘璁や环鍖洪棿
input int    InpConfirmPullbackWaitSec = 30; // 鍥炶俯绛夊緟绉掓暟
input double InpConfirmPullbackMaxAdversePct = 0.20; // 鍙嶅悜璺岀牬瑙︾偣瀹瑰繊OB楂樺害姣斾緥
input bool   InpEnableEntryMomentumFilter = false; // 鍚敤鍏ュ満寮哄急杞崲杩囨护
input int    InpEntryMomentumTF = 1;         // 鍏ュ満寮哄急杩囨护鍛ㄦ湡(鍒嗛挓,0=宸ヤ綔鍛ㄦ湡)
input bool   InpEntryBlockCounterStrong = true; // 鍙嶅悜寮哄娍鏈浆寮辨椂绂佹鍏ュ満
input bool   InpEntryRequireCounterWeak = false; // 鍏ュ満蹇呴』鍑虹幇鍙嶅悜瓒嬪娍杞急璇佹嵁
input bool   InpEnableEntryStructureConfirm = false; // 入场前要求小周期结构突破/动能延续确认
input string InpEntryStructureConfirmFamilies = ""; // 仅确认指定信号族(SWP,OB,BOS,MBOS; 空=全部)
input string InpEntryStructureConfirmOBDirections = ""; // OB结构确认方向: BUY,SELL; 空=沿用信号族规则
input int    InpEntryStructureConfirmTF = 1; // 结构确认周期(分钟)
input int    InpEntryStructureLookbackBars = 24; // 最近强弱高低点扫描窗口
input int    InpEntryStructurePivotBars = 1; // swing强度
input double InpEntryStructureBreakBufferATR = 0.03; // 收盘突破缓冲(ATR)
input bool   InpEntryStructureRequireBreak = true; // 入场结构确认是否要求小周期结构突破
input double InpEntryStructureMinNetATR = 0.12; // 同向实体净推进/ATR下限
input int    InpEntryStructureNetBars = 2; // 净推进观察K数
input double InpEntryStructureReverseBodyATR = 0.45; // 强反向K实体阈值(ATR)
input bool   InpEnableEntryHTFShapeFilter = false; // 入场前HTF实体/位置过滤
input int    InpEntryHTFShapeTF = 240; // HTF形态过滤周期(分钟)
input int    InpEntryHTFShapeBars = 4; // HTF区间观察K数
input double InpEntryHTFMaxSameBody = 0.0; // 最近HTF同向实体上限(价格单位,0=不限制)
input double InpEntryHTFMaxRangePos = 0.0; // 入场价在HTF区间方向位置上限(0=不限制)
input bool   InpEnableEntryExhaustionFilter = false; // 入场前短周期同向过度推进过滤
input int    InpEntryExhaustionTF = 5; // 同向过度推进观察周期(分钟)
input int    InpEntryExhaustionBars = 6; // 同向过度推进观察K数
input double InpEntryExhaustionMaxNet = 0.0; // 同向净推进上限(价格单位,0=不限制)
input bool   InpEnableEntryContextFilter = false; // 入场前多周期净推进上下文过滤
input int    InpEntryContextTF = 60; // 上下文过滤周期(分钟)
input int    InpEntryContextBars = 6; // 上下文过滤观察K数
input double InpEntryContextMinNet = -999999.0; // 原始净推进下限(价格单位)
input double InpEntryContextMaxNet = 999999.0; // 原始净推进上限(价格单位)
input double InpEntryContextMinEfficiency = 0.0; // 净推进效率下限(abs(net)/range, 0=不限制)
input int    InpEntryContextTF2 = 0; // 第二上下文过滤周期(分钟,0=禁用)
input int    InpEntryContextBars2 = 1; // 第二上下文过滤观察K数
input double InpEntryContextMinNet2 = -999999.0; // 第二原始净推进下限
input double InpEntryContextMaxNet2 = 999999.0; // 第二原始净推进上限
input double InpEntryContextMinEfficiency2 = 0.0; // 第二净推进效率下限
input bool   InpEnableEntryDirContextFilter = false; // 入场前按交易方向过滤净推进
input bool   InpEntryDirContextApplyBuy = true; // 方向上下文过滤作用于做多
input bool   InpEntryDirContextApplySell = true; // 方向上下文过滤作用于做空
input int    InpEntryDirContextTF = 15; // 方向上下文周期(分钟)
input int    InpEntryDirContextBars = 8; // 方向上下文观察K数
input double InpEntryDirContextMinNet = -999999.0; // 方向净推进下限(net*direction)
input double InpEntryDirContextMaxNet = 999999.0; // 方向净推进上限(net*direction)
input int    InpEntryDirContextTF2 = 0; // 第二方向上下文周期(分钟,0=禁用)
input int    InpEntryDirContextBars2 = 1; // 第二方向上下文观察K数
input double InpEntryDirContextMinNet2 = -999999.0; // 第二方向净推进下限
input double InpEntryDirContextMaxNet2 = 999999.0; // 第二方向净推进上限
input bool   InpEnableSWPContinuationConfirm = false; // SWP入场要求扫损后小周期同向延续
input int    InpSWPContinuationTF = 5; // SWP延续确认周期(分钟)
input int    InpSWPContinuationBars = 2; // SWP延续确认K线数
input double InpSWPContinuationMinNetATR = 0.20; // SWP同向净实体推进阈值(ATR)
input double InpSWPContinuationReverseBodyATR = 0.45; // SWP强反向K实体阈值(ATR)
input double InpSWPContinuationBreakBufferATR = 0.05; // SWP反向微结构突破缓冲(ATR)
input double InpSWPContinuationFailMult = 0.0; // SWP延续确认失败仓位倍数(<=0过滤)
input bool   InpRequireDoubleTch = true;     // 瑕佹眰浜屾瑙︾
input int    InpDoubleTchWindowMin = 60;     // 浜屾瑙︾绐楀彛(鍒嗛挓)
input double InpMinOBSpreadMult  = 2.0;      // 鏈€灏廜B瀹藉害(鐐瑰樊鍊嶆暟)
input double InpMinRiskSpreadRatio = 3.0;    // 鏈€灏忛闄?鐐瑰樊姣?
input double InpMinAbsRiskUSD    = 0.0;      // 鏈€灏忕粷瀵归闄?USD)
// --- 入场噪声自适应 (Noise-Adaptive Entry, 全部opt-in) ---
input bool   InpEnableTickNoiseGate     = false;  // Tick噪声门控总开关
input int    InpTickNoiseGateLookback   = 30;     // 回溯tick数
input double InpTickNoiseGateMinDirRatio = 0.35; // 最小tick方向一致率(<此值拒绝)
input double InpTickNoiseGateMaxRangeATR = 0.15; // 最大tick振幅/ATR比(>此值拒绝)
// --- 自适应噪音门控: 根据实时权益回撤动态切换噪音参数(全部opt-in) ---
input double InpAdaptiveNoiseDrawdownPct  = 0.0;  // 权益从峰值回撤%触发防守噪音(0=禁用, 建议2.0)
input double InpAdaptiveNoiseDefMinDirRatio = 0.45; // 防守态tick方向一致率(严, <此值拒绝)
input double InpAdaptiveNoiseDefMaxRangeATR = 0.10; // 防守态最大tick振幅/ATR(严, >此值拒绝)
input double InpAdaptiveNoiseRecoveryPct  = 1.0;  // 恢复到峰值该%内退出防守(0=不恢复, 建议1.0)
input double InpAdaptiveNoiseDefBoostMult = 0.6; // 防守态仓位乘数衰减(1=不衰减,0=全平仓,建议0.5-0.7)
input int    InpAdaptiveNoiseDefCooldownBars = 0;   // 防守态全局冷卻bars(0=禁用,建议20-30)
input double InpAdaptiveNoiseDefBuyMult  = 1.0;   // 防守态买单仓位乘数(1=不调整,建议0.5)
input double InpAdaptiveNoiseDefSellMult = 1.0;   // 防守态卖单仓位乘数(1=不调整,建议0.5)
input int    InpAdaptiveNoiseDefOBReentryCd = 0;    // 防守态同OB重入冷卻(分钟,0=禁用,建议5-10)
input double InpAdaptiveNoiseDefNeutralMult = 1.0; // 防守态Neutral趋势仓位乘数(1=不调整,0=拦截无趋势交易,建议0.0)
// --- Mitigation Entry: 震荡市等价格回归OB消解后再入场(P0 SMC改进) ---
input bool   InpEnableMitigationEntry = false;    // 启用Mitigation Entry(震荡市替代Bounce Entry,先扫荡完成→等价格回归OB消解→入场)
input int    InpMitigationEntryMaxBars = 10;     // 等价格回归OB的最大bars数(超时过期,建议5-15)
input bool   InpMitigationEntryOnlyRange = true; // 仅在震荡市(market_state=0)启用Mitigation,趋势市保留原Bounce
input bool   InpMitigationEntryOnlyDefensive = true; // 仅在自适应防守态(权益回撤)启用Mitigation,正常态保留Bounce
input string InpMitigationEntrySignalTypes = "sweep"; // 启用的信号类型(all/sweep/ob/range/htfpb)
// --- 双扫确认: 要求双方向LP都被扫荡后才允许入场(SMC路径B) ---
input bool   InpEnableDoubleSweepConfirm = false;   // 启用双扫确认(上下LP都被扫后才入场)
input int    InpDoubleSweepWindowBars = 20;         // 双扫确认窗口bars(价格需在此窗口内扫过两侧LP)
input bool   InpDoubleSweepOnlyDefensive = true;    // 仅在防守态启用(趋势月不受影响)
input bool   InpDoubleSweepBlockSweepEntry = false; // 双扫确认后禁用Sweep OB入场(仅保留普通OB)
input double InpDoubleSweepDTPTriggerR = 0.0;       // 双扫防守态DTP触发R(0=用正常值, 建议0.5匹配窄幅区间)
input double InpDoubleSweepRegimePosMult = 1.0;     // 双扫体制仓位乘数(<1=震荡区间降仓位, 1=不调整, 建议0.6)
// --- FVG (公允价值缺口): SMC三要素第三原语, 震荡市fade信号核心 ---
input bool   InpEnableFVG = false;              // 启用FVG检测(公允价值缺口, 震荡市替代信号源)
input int    InpFVGLookbackBars = 30;           // FVG扫描回溯bars(3=仅检测最新, 建议20-50)
input double InpFVGMinGapATR = 0.08;            // 最小FVG缺口/ATR(过滤微缺口, 建议0.05-0.15)
input double InpFVGMaxGapATR = 0.80;            // 最大FVG缺口/ATR(过滤极端缺口, 0=不限制)
input int    InpFVGMaxAgeBars = 60;             // FVG最大存活bars(超过自动过期, 0=用全局InpBars)
input int    InpFVGTimeoutMin = 180;            // FVG时间过期(分钟, 0=不限制)
input bool   InpFVGRequireRangeBoundary = true; // 仅震荡区间边界附近的FVG有效(过滤趋势中途FVG)
input bool   InpFVGEnableFadeEntry = false;     // 启用FVG fade入场(震荡市FVG回补后反向入场)
input double InpFVGFadeMinRiskSpreadRatio = 3.0;// FVG fade入场最小risk/spread比
input double InpFVGFadeMaxEntryOffsetR = 1.2;   // FVG fade入场最大偏移R
input double InpFVGFadePosMult = 0.5;           // FVG fade仓位乘数(相对正常仓位, 建议0.3-0.7)
input double InpFVGFadeMaxLotSize = 0.02;       // FVG fade最大手数(小资金保守, 建议0.01-0.03)
input double InpFVGFadeTPMult = 1.0;            // FVG fade TP=区间高度倍数(0=DTP接管)
input string InpFVGNoEntryHours = "5,6,7";     // FVG专属禁入时段UTC CSV(空=不限制, 建议5,6,7避开伦敦开盘噪音)
input bool   InpFVGRequireConfirmCandle = false; // FVG回补后需要同向确认K线(类似EntryEngine的Bounce确认)
input bool   InpFVGRequireH1Aligned = false;    // FVG入场必须与H1 OB方向对齐(趋势市=同向, 震荡市=fade顺H1)
input bool   InpEnableHTFDirectionGate = false; // HTF方向门控: 直接拦截强逆势入场(不经过仓位乘数, 零代码改动仅.set)
// --- ATR体制检测: 基于市场微观结构的前向检测(全部opt-in) ---
input int    InpATRRegimePeriod        = 0;    // 历史ATR基准bars(0=禁用,建议100=~1.5h M1)
input double InpATRRegimeLowThreshold  = 0.7;  // 当前ATR/历史ATR<此值→低波防守
input double InpATRRegimeLowMaxPosMult = 1.0;  // 低波体制最大仓位乘数(1=不调整,建议0.8)
input double InpATRRegimeLowDTPTriggerR = 0.0; // 低波体制DTP触发R(0=用正常值,建议0.75)
input double InpMinSLSpreadMult    = 0.0;      // 最小SL=spread*倍数(0=禁用)
input int    InpOBTouchConfirmTicks = 0;       // OB接触确认tick数(0=禁用)
input bool   InpEnableDynamicSpread  = false;  // 动态spread感知
input double InpMinOBBodyPct     = 50.0;     // OB铚＄儧鏈€灏忓疄浣撳崰姣?%)
input double InpMinImpulseBodyPct = 0.0;     // 浣嶇ЩK绾挎渶灏忓疄浣撳崰姣?%)
input double InpMinImpulseVolRatio = 0.0;    // 浣嶇ЩK绾挎渶灏忔垚浜ら噺鍊嶇巼(0=绂佺敤)
input int    InpStructureBreakBars = 0;      // 涓ユ牸缁撴瀯绐佺牬绐楀彛(0=浠呯敤鏃ap2)
input double InpStructureBreakATR = 0.0;     // 涓ユ牸缁撴瀯绐佺牬棰濆ATR闃堝€?
input bool   InpRequireImpulseCandleDir = false; // 浣嶇ЩK蹇呴』鍚屾柟鍚戞敹鐩?
input bool   InpEnableRangeBreakout = false; // 鍚敤闇囪崱鍖洪棿鏈夋晥绐佺牬鍏ュ満
input bool   InpRangeBreakoutOnly = false;   // 浠呬氦鏄撻渿鑽″尯闂寸獊鐮达紝鍏抽棴甯歌OB
input int    InpRangeBreakoutBars = 10;      // 闇囪崱鍖洪棿瑙傚療bar鏁?
input double InpRangeBreakoutMaxATR = 1.20;  // 鍖洪棿鏈€澶ч珮搴?ATR
input double InpRangeBreakoutMinSpreadMult = 3.0; // 鍖洪棿鏈€灏忛珮搴?spread
input double InpRangeBreakoutATR = 0.10;     // 鏈夋晥绐佺牬棰濆ATR闃堝€?
input double InpRangeBreakoutTPMult = 1.0;   // TP=鍖洪棿楂樺害鍊嶆暟(0=涓嶇敤鍥哄畾TP)
input bool   InpRangeBreakoutBodyDir = true; // 绐佺牬K蹇呴』鍚屾柟鍚戝疄浣?
input bool   InpEnableLiquiditySweep = false; // 鍚敤娴佸姩鎬ф壂鎹熷弽杞叆鍦?
input bool   InpLiquiditySweepOnly = false;   // 浠呬氦鏄撴壂鎹熷弽杞紝鍏抽棴甯歌OB
input int    InpSweepLookbackBars = 12;       // 鎵崯鍙傝€冨尯闂碽ar鏁?
input double InpSweepMaxRangeATR = 2.50;      // 鍙傝€冨尯闂存渶澶ч珮搴?ATR
input double InpSweepMinRangeSpreadMult = 4.0; // 鍙傝€冨尯闂存渶灏忛珮搴?spread
input double InpSweepMinPenetrationATR = 0.05; // 鎵牬鍖洪棿棰濆ATR闃堝€?
input double InpSweepMinWickPct = 45.0;       // 鎵崯K鏈€灏忓奖绾垮崰姣?
input double InpSweepTPMult = 1.0;            // TP=鍘熷尯闂撮珮搴﹀€嶆暟(0=DTP)
input bool   InpEnableLooseSweep = false;     // 鍚敤绗簩鏉″鏉維weep琛ラ鑵?
input int    InpLooseSweepLookbackBars = 6;   // 瀹芥澗Sweep鍙傝€冨尯闂碽ar鏁?
input double InpLooseSweepMaxRangeATR = 4.0;  // 瀹芥澗Sweep鍙傝€冨尯闂存渶澶ч珮搴?ATR
input double InpLooseSweepMinRangeSpreadMult = 2.5; // 瀹芥澗Sweep鏈€灏忛珮搴?spread
input double InpLooseSweepMinPenetrationATR = 0.01; // 瀹芥澗Sweep鎵牬ATR闃堝€?
input double InpLooseSweepMinWickPct = 30.0;  // 瀹芥澗Sweep鏈€灏忓奖绾垮崰姣?
input int    InpNoOBStartHour    = 23;       // 绂佹寤篛B寮€濮嬪皬鏃?鏈嶅姟鍣ㄦ椂闂?-1=绂佺敤)
input int    InpNoOBEndHour      = 6;        // 绂佹寤篛B缁撴潫灏忔椂(鏈嶅姟鍣ㄦ椂闂?-1=绂佺敤)
input double InpMinOBStrength    = 0.5;      // 鏈€浣嶰B寮哄害
input double InpMaxRiskATR       = 3.0;      // 鏈€澶isk/ATR
input double InpMaxCounterRiskATR = 1.5;     // 閫嗗娍鏈€澶isk/ATR
input bool   InpConsolidateOB    = true;     // 鍚堝苟閲嶅彔OB
input double InpSpreadFloor      = 0.0;      // 鏈€灏弒pread涓嬮檺(0=浣跨敤瀹炴椂spread)

// 鈹€鈹€ Impulse鍙傛暟 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpImpulseATRMult   = 1.5;      // Impulse鍒ゅ畾闃堝€?ATR鍊嶆暟)
input int    InpImpulseLookback  = 3;        // Impulse瑙傚療绐楀彛(bars)
input int    InpATRPeriod        = 14;       // ATR璁＄畻鍛ㄦ湡

// 鈹€鈹€ 姝㈡崯 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpSLBufferATR      = 0.10;     // SL棰濆ATR缂撳啿
input int    InpVirtualSLConfirmBars = 0;    // 虚拟止损连续收盘确认根数(0=禁用)
input int    InpVirtualSLConfirmTF = 1;      // 虚拟止损确认周期(分钟)
input double InpVirtualSLHardBufferR = 0.0;  // 券商硬止损额外放宽R倍数(0=禁用)
input int    InpVirtualSLBreachSec = 0;         // VSL breach seconds: exit after N seconds sustained break (0=disabled, suggest 3-10)
input double InpVirtualSLCloseBufferATR = 0.0; // 收盘确认需越过原始SL的ATR缓冲
input int    InpDefensiveVirtualSLConfirmBars = 0; // Defensive virtual SL confirm bars
input double InpDefensiveVirtualSLHardBufferR = 0.0; // Defensive hard stop buffer in R
input double InpDefensiveVirtualSLCloseBufferATR = 0.0; // Defensive virtual SL close buffer

// 鈹€鈹€ 淇濇湰 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpBreakevenR       = 0.2;      // 淇濇湰瑙﹀彂(R鍊嶆暟)
input double InpBreakevenLockR   = 0.05;     // 淇濇湰閿佸畾鍒╂鼎(R鍊嶆暟)
input double InpBreakevenStage2R = 0.0;      // 渐进保本阶段2触发R(0=禁用)
	input double InpBreakevenStage2LockR = 0.0;  // 渐进保本阶段2锁定R
input double InpEarlyLossCutR    = 0.0;      // 鍏ュ満鍚庢湭淇濇湰鍓嶄富鍔ㄥ皬浜忛€€鍑篟(0=绂佺敤)
input double InpMFEFailMinR      = 0.0;      // 鏇捐揪鍒拌娴泩鍚庡惎鐢ㄥけ璐ラ€€鍑?0=绂佺敤)
input double InpMFEFailExitR     = 0.0;      // 娴泩鍚庡洖钀借嚦璇涓诲姩閫€鍑?
input int    InpNoMFEExitBars    = 0;        // 鎸佷粨N鏍瑰悗浠嶆棤鏈€灏忔诞鐩堝垯閫€鍑?0=绂佺敤)
input double InpNoMFEMinPeakR    = 0.0;      // 鍒ゆ柇鏈夋诞鐩堢殑鏈€灏忓嘲鍊糝
input double InpNoMFEExitR       = 0.0;      // 鏃犳诞鐩堝け璐ラ€€鍑虹殑褰撳墠R闃堝€?
input bool   InpEnableFailureReentryConfirm = false; // 连续主动失败后, 同向重入需小周期延续确认
input int    InpFailureReentryConfirmLosses = 2; // 触发确认所需连续同向主动失败次数
input int    InpFailureReentryConfirmTF = 1; // 重入确认周期(分钟)
input int    InpFailureReentryConfirmBars = 2; // 重入确认观察bar数
input double InpFailureReentryConfirmMinATR = 0.12; // 同向实体净推进/ATR下限
input bool   InpFailureReentryRequireStructureBreak = false; // 重入需小周期收盘突破最近强弱高低点
input int    InpFailureReentryStructureLookbackBars = 24; // 重入结构扫描窗口
input int    InpFailureReentryStructurePivotBars = 1; // 重入结构swing强度
input double InpFailureReentryBreakBufferATR = 0.03; // 重入结构突破缓冲(ATR)
input double InpFailureReentryReverseBodyATR = 0.45; // 强反向K实体阈值(ATR)
input bool   InpFailureReentryBlockStrongReverse = false; // 有强反向K则禁止重入
input bool   InpFailureReentryBlockReverseBreak = false; // 有反向结构突破则禁止重入
input double InpFailureReentryConfirmMaxAgeMin = 180.0; // 连续失败状态有效分钟数(0=不限)
input double InpFailureReentryBlockMin = 0.0; // 连续主动失败后同向重入禁用分钟数(0=用延续确认)
input bool   InpFailureReentryBlockOBOnly = false; // 连续失败阻断仅作用于普通OB, 放行Sweep
input double InpFailureReentryBlockMinPosMult = 0.0; // 连续失败阻断仅作用于仓位倍数>=该值的信号(0=不限)
input double InpFailureReentryClearWinR = 0.0; // 盈利出场达到该R后清空连续失败状态(0=任意盈利清空, <0=不清空)
input bool   InpFailureReentryRecordPassiveLoss = false; // broker SL/BE等被动失败也计入同向重入确认
input double InpFailureReentryPassiveLossMaxPeakR = 0.5; // 峰值低于该R的被动消失视为失败
input string InpFailureReentryFamilyFilter = ""; // 仅记录/限制指定信号族(SWP,OB,BOS,MBOS,SDFLIP; 空=全部)
input double InpPostWinCooldownMinProfit = 0.0; // 平仓盈利达到该金额后触发同族冷却(0=禁用)
input int    InpPostWinCooldownMin = 0; // 盈利后同族冷却分钟数(0=禁用)
input string InpPostWinCooldownFamilies = ""; // 盈利后冷却作用信号族(BOS,OB,SWP; 空=全部)
input bool   InpPostWinCooldownSameDirection = true; // true=仅冷却同方向, false=同族全方向
input bool   InpPostWinCooldownCrossFamily = false; // true=盈利后冷却作用于过滤范围内全部信号族
input bool   InpPostWinCooldownBlockEntries = true; // true=冷却期直接阻断, false=仅用于限仓
input double InpPostWinCooldownMaxLotSize = 0.0; // 冷却期内最大手数(0=不限)
input bool   InpEnableBalanceTierLotCap = false; // 启用余额阶梯仓位上限(opt-in默认关闭)
input double InpBalanceTier1Threshold = 5000.0;   // 阶梯1余额阈值(余额<该值时启动上限)
input double InpBalanceTier1MaxLotSize = 1.0;     // 阶梯1仓位上限(余额<阈值时仓位不超过该值)
input double InpBalanceTier1OBSignalMaxLotSize = 1.0;  // 阶梯1 OB 信号仓位上限(默认 1.0=不限)
input double InpBalanceTier1SWPMaxLotSize = 1.0;   // 阶梯1 SWP 信号仓位上限(默认 1.0=不限)
input double InpBalanceTier1BOSMaxLotSize = 1.0;   // 阶梯1 BOS 信号仓位上限(默认 1.0=不限)
input double InpBalanceTier1OtherMaxLotSize = 1.0; // 阶梯1 其他 信号仓位上限
input bool   InpPostWinCooldownRequireContinuation = false; // 冷却期内允许小周期延续确认后同向再入场
input int    InpPostWinCooldownContinuationTF = 5; // 盈利后再入场延续确认周期(分钟)
input int    InpPostWinCooldownContinuationBars = 2; // 盈利后再入场净推进K数
input double InpPostWinCooldownContinuationMinNetATR = 0.20; // 盈利后再入场净实体推进/ATR下限
input bool   InpPostWinCooldownContinuationRequireBreak = true; // 盈利后再入场是否要求小周期结构突破
input double InpPostWinCooldownContinuationBreakBufferATR = 0.05; // 盈利后再入场结构突破缓冲(ATR)
input double InpPostWinCooldownContinuationReverseBodyATR = 0.45; // 盈利后再入场强反向K实体阈值(ATR)
input bool   InpEnableFailureReverse = false; // 涓诲姩澶辫触閫€鍑哄悗鍙嶅悜寮€鍗?
input bool   InpReverseOnEarlyLoss = false;  // early_loss鍚庡弽鎵?
input bool   InpReverseOnMFEFail   = false;  // mfe_fail鍚庡弽鎵?
input bool   InpReverseOnNoMFE     = false;  // no_mfe鍚庡弽鎵?
input double InpFailureReverseRiskMult = 1.0; // 鍙嶆墜鍗昐L璺濈=鍘熷risk鍊嶆暟
input double InpFailureReverseLotMult  = 1.0; // 鍙嶆墜鍗曚粨浣嶅€嶆暟
input double InpFailureReverseTPR      = 0.0; // 鍙嶆墜鍥哄畾TP R(0=娌跨敤DTP)
input bool   InpFailureReverseAllowChain = false; // 鍏佽鍙嶆墜鍗曠户缁弽鎵?

// 鈹€鈹€ 杩借釜姝㈡崯 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpTrail1TriggerR   = 1.0;      // 杩借釜1瑙﹀彂(R)
input double InpTrail1LockR      = 0.2;      // 杩借釜1閿佸畾(R)
input double InpTrail2TriggerR   = 2.5;      // 杩借釜2瑙﹀彂(R)
input double InpTrail2LockR      = 0.0;      // 杩借釜2閿佸畾(R, 鍥哄畾)
input double InpTrail2LockMult   = 0.65;     // 杩借釜2閿佸畾(涔樻暟)

bool CfgBTCBigWinLock()  { return UseBTCProfile() ? InpBTCBigWinLock  : false; }
double CfgBTCBigWinLockR()  { return UseBTCProfile() ? InpBTCBigWinLockR  : 999.0; }
double CfgBTCBigWinLockRR() { return UseBTCProfile() ? InpBTCBigWinLockRR : 0.5; }
input double InpTrail3TriggerR   = 0.0;      // 杩借釜3瑙﹀彂(R, 0=绂佺敤)
input double InpTrail3LockR      = 0.0;      // 杩借釜3閿佸畾(R)
input double InpTrail3LockMult   = 0.0;      // 杩借釜3閿佸畾(涔樻暟)

// BTC Big Win Lock - 当R>=3R时自动trail锁定部分利润 (防big_w回吐)
input bool   InpBTCBigWinLock      = true;     // BTC 大赢单保护器启用
input double InpBTCBigWinLockR     = 0.5;      // BTC 大赢单锁定阈值(R), R>=此值开始锁利
input double InpBTCBigWinLockRR    = 0.3;      // BTC 大赢单锁定后回撤触发(R, peak-R < LockRR时关闭)

// 鈹€鈹€ DTP (鍔ㄦ€佹鐩? 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpDTPTriggerR      = 1.5;      // DTP婵€娲婚槇鍊?R, 0=绂佺敤)
input double InpDTPRetrace       = 0.30;     // DTP鍥炴挙鍏抽棴姣斾緥
input bool   InpAdaptiveDTP      = true;     // 鑷€傚簲DTP
input double InpDTPStage2TriggerR = 0.0;     // DTP浜岄樁瑙﹀彂宄板€糝(0=绂佺敤)
input double InpDTPStage2Retrace = 0.0;      // DTP浜岄樁鍥炴挙姣斾緥(0=绂佺敤)
input double InpDTPStage3TriggerR = 0.0;     // DTP涓夐樁瑙﹀彂宄板€糝(0=绂佺敤)
input double InpDTPStage3Retrace = 0.0;      // DTP涓夐樁鍥炴挙姣斾緥(0=绂佺敤)
input int    InpDTPExitMode      = 0;        // DTP閫€鍑烘ā寮?0=鍏ㄥ钩,1=鍏堥儴鍒嗗钩浠?
input int    InpDTPPartialPct    = 50;       // DTP閮ㄥ垎骞充粨姣斾緥(%)
input double InpDTPPostPartialRetrace = 0.0; // DTP閮ㄥ垎骞充粨鍚庡洖鎾ゆ瘮渚?0=娌跨敤)
input double InpDTPPostPartialLockR = 0.0;   // DTP閮ㄥ垎骞充粨鍚庡墿浣欎粨SL閿佸畾R(0=绂佺敤)
input bool   InpDTPResetPeakAfterPartial = false; // DTP閮ㄥ垎骞充粨鍚庨噸缃綑浠撳嘲鍊?
input double InpFixedTPR         = 0.0;      // 鍥哄畾姝㈢泩(R, 0=DTP妯″紡)
input double InpOBHeightTPMult   = 0.0;      // TP=OB楂樺害鍊嶆暟(0=绂佺敤,2=閲忓害绉诲姩)

// 鈹€鈹€ 鍒嗗眰鍏ュ満(闇囪崱缃戞牸) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input int    InpLayeredEntryCount = 0;       // 鍒嗗眰鍏ュ満鏁?0=绂佺敤,2-3=鍒嗗眰)
input double InpLayeredSpacingPct = 0.33;    // 鍒嗗眰闂磋窛(OB楂樺害鐧惧垎姣?
input double InpLayeredLotMult    = 1.5;     // 娣卞眰浠撲綅鍊嶆暟(鐩稿棣栧眰)
input double InpLayeredAvgTP_R    = 0.0;     // 浠庡潎浠风畻TP(R,0=鐢ㄥ叾浠朤P)
input int    InpMicroEntryCount   = 0;       // 鍚屼俊鍙峰井浠撳壇鍗曟暟(0=绂佺敤)
input double InpMicroEntryLotMult = 0.05;    // 寰粨鍓崟鎵嬫暟鍊嶆暟(鐩稿涓诲崟)
input double InpMicroEntryMaxLotSize = 0.0;  // 寰粨鍓崟鏈€澶ф墜鏁?0=涓嶉檺鍒?

// 鈹€鈹€ 鏃堕棿閫€鍑?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input int    InpTimeExitBars     = 999;      // 瓒呮椂閫€鍑?bars, 999=绂佺敤)
input bool   InpTimeDecayTP      = false;    // 鏃堕棿琛板噺TP

// 鈹€鈹€ 浠撲綅绠＄悊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpRiskPercent      = 2.0;      // 鍗曠瑪椋庨櫓(%浣欓)
input double InpFixedLotSize     = 0.0;      // 鍥哄畾鎵嬫暟(>0鏃跺拷鐣ラ闄?)
input bool   InpEnablePosMult    = true;     // 鍚敤浠撲綅涔樻暟(false=鍥哄畾1.0)
input double InpMaxPosMult       = 0.0;      // 鏈€澶т粨浣嶄箻鏁?0=涓嶉檺鍒?
input double InpMaxLotSize       = 0.0;      // 鏈€澶ф墜鏁?0=涓嶉檺鍒?
input double InpHighPosMultCapThreshold = 0.0; // 仓位倍数达到该阈值后启用手数上限(0=禁用)
input double InpHighPosMultMaxLotSize = 0.0;   // 高仓位倍数订单最大手数(0=禁用)
input string InpHighPosMultCapDirections = ""; // 高仓位倍数限仓方向: BUY,SELL; 空=全部方向
input double InpSweepPosMult     = 1.0;      // 鎵崯鍙嶈浆淇″彿浠撲綅鍊嶆暟
input double InpSweepH1AlignedMult = 1.0;    // Sweep且H1对齐时仓位倍数(<=0=过滤)
input double InpRangeBreakoutPosMult = 1.0;  // 鍖洪棿绐佺牬淇″彿浠撲綅鍊嶆暟
input double InpHTFPullbackPosMult = 1.0;    // HTF鍥炶俯淇″彿浠撲綅鍊嶆暟
input double InpSweepMaxLotSize  = 0.0;      // 鎵崯鍙嶈浆淇″彿鏈€澶ф墜鏁?0=涓嶉檺鍒?
input double InpLooseSweepPosMult = 0.05;    // 瀹芥澗Sweep琛ラ鑵夸粨浣嶅€嶆暟
input double InpLooseSweepMaxLotSize = 0.005; // 瀹芥澗Sweep琛ラ鑵挎渶澶ф墜鏁?0=涓嶉檺鍒?
input int    InpLooseSweepMaxActiveZones = 20; // max active loose sweep zones (0=unlimited)
input double InpRangeBreakoutMaxLotSize = 0.0; // 鍖洪棿绐佺牬淇″彿鏈€澶ф墜鏁?0=涓嶉檺鍒?
input double InpHTFPullbackMaxLotSize = 0.0; // HTF鍥炶俯淇″彿鏈€澶ф墜鏁?0=涓嶉檺鍒?
input int    InpHTFPullbackMinDay = 0;       // HTF回踩补位最早启用日(0=禁用)
input int    InpHTFPullbackMaxMonthlyEntries = -1; // HTF回踩补位仅在月内成交数<=该值时启用(-1=禁用)
input string InpHTFPullbackAllowHours = ""; // HTF鍥炶俯鍏佽灏忔椂CSV(绌?鍏ㄩ儴鍏佽)
input string InpHTFPullbackNoHours = "";    // HTF鍥炶俯绂佹灏忔椂CSV(绌?绂佺敤)
input double InpHTFPullbackRiskMin = 0.0;   // HTF鍥炶俯椋庨櫓涓嬮檺(0=绂佺敤)
input double InpHTFPullbackRiskMax = 0.0;   // HTF鍥炶俯椋庨櫓涓婇檺(<=min=绂佺敤)
input double InpHTFPullbackConfirmMin = -999.0; // HTF鍥炶俯纭浣嶇疆涓嬮檺
input double InpHTFPullbackConfirmMax = 999.0;  // HTF鍥炶俯纭浣嶇疆涓婇檺
input double InpHTFPullbackContextMult = 1.0;   // HTF鍥炶俯涓婁笅鏂囦粨浣嶅€嶆暟(<=0=杩囨护)
input bool   InpHTFBOSRetestEntry = false;     // HTF BOS突破回踩入场
input bool   InpHTFBOSRetestDirectEntry = false; // BOS回踩直接入场(当前WaiTrade2保留, 默认走EntryEngine确认)
input int    InpHTFBOSRetestTF = 60;           // BOS主检测周期(分钟)
input int    InpHTFBOSRetestTF2 = 240;         // BOS第二检测周期(分钟,0=禁用)
input int    InpHTFBOSRetestLookbackBars = 96; // BOS swing扫描窗口
input int    InpHTFBOSRetestPivotBars = 2;     // BOS强高低点pivot强度
input double InpHTFBOSRetestBreakBufferATR = 0.05; // BOS收盘突破缓冲(ATR)
input double InpHTFBOSRetestMinExtensionATR = 0.50; // BOS突破后最小延伸(ATR)
input double InpHTFBOSRetestTolerance = 0.30;  // BOS回踩区半宽(ATR)
input int    InpHTFBOSRetestMaxBars = 720;     // BOS回踩区最大有效bar数
input double InpHTFBOSRetestWeight = 1.0;      // BOS回踩仓位倍数
input double InpHTFBOSRetestSLBuffer = 0.5;    // BOS回踩SL额外缓冲(ATR)
input double InpHTFBOSRetestMaxLotSize = 0.0;  // BOS回踩最大手数(0=不限制)
input bool   InpHTFBOSRequireOBConfluence = false; // BOS回踩要求HTF订单块共振
input int    InpHTFBOSOBLookbackBars = 24;     // BOS附近HTF订单块扫描窗口
input double InpHTFBOSOBToleranceATR = 0.60;   // BOS level与HTF订单块最大距离(ATR)
input double InpHTFBOSOBMinImpulseATR = 0.60;  // HTF订单块后同向冲动最小ATR
input string InpSweepAllowHours  = "";       // Sweep鍏佽灏忔椂CSV(绌?鍏ㄩ儴鍏佽)
input string InpSweepNoHours     = "";       // Sweep绂佹灏忔椂CSV(绌?绂佺敤)
input string InpSweepContextMonths = "";     // Sweep涓婁笅鏂囪繃婊ゆ湀浠紺SV(绌?鍏ㄩ儴鏈堜唤)
input int    InpSweepContextMaxDay = 0;      // Sweep涓婁笅鏂囪繃婊や粎鏈堝唴鍓峃澶╁惎鐢?0=涓嶉檺)
input double InpSweepContextMinMonthStartBalance = 0.0; // Sweep涓婁笅鏂囪繃婊ゆ湀鍒濅綑棰濅笅闄?0=涓嶉檺)
input string InpSweepContextNoHours = "";   // Sweep涓婁笅鏂囬澶栫姝㈠皬鏃禖SV(绌?绂佺敤)
input double InpSweepBadRiskMin  = 0.0;      // Sweep寮遍闄╁尯闂翠笅闄?
input double InpSweepBadRiskMax  = 0.0;      // Sweep寮遍闄╁尯闂翠笂闄?
input double InpSweepBadRiskMult = 1.0;      // Sweep寮遍闄╁尯闂翠粨浣嶅€嶆暟(<=0杩囨护)
input double InpSweepMinBalance  = 0.0;      // 浣欓浣庝簬璇ュ€兼椂杩囨护Sweep(0=绂佺敤)
input double InpSweepLowBalanceThreshold = 0.0; // 浣欓浣庝簬璇ュ€兼椂Sweep闄嶆潈(0=绂佺敤)
input double InpSweepLowBalanceMult = 1.0;   // 浣庝綑棰漇weep浠撲綅鍊嶆暟(<=0杩囨护)
input double InpSweepMonthlyNegativeMult = 1.0; // 鏈堝唴浣欓浣庝簬鏈堝垵鏃禨weep浠撲綅鍊嶆暟(<=0杩囨护)
input bool   InpSweepOnlyMonthlyNegative = false; // Sweep仅在月内余额低于月初时启用
input double InpSweepMonthlyProfitStartPct = 0.0; // 鏈堝唴鐩堝埄杈惧埌鏈堝垵璇ョ櫨鍒嗘瘮鍚庢墠鍏佽Sweep(0=绂佺敤)
input int    InpSweepEarlyBounceSecMin = 0; // Sweep early confirmation lower bound seconds (0=disabled)
input int    InpSweepEarlyBounceSecMax = 0; // Sweep early confirmation upper bound seconds (<=min=disabled)
input double InpSweepEarlyBounceMult = 1.0; // Sweep early confirmation position multiplier (<=0=filter)
input string InpSweepEarlyBounceHours = ""; // CSV hours where early confirmation multiplier applies (empty=all hours)
input int    InpSweepLateBounceSecMin = 0; // Sweep late confirmation lower bound seconds (0=disabled)
input double InpSweepLateBounceMult = 1.0; // Sweep late confirmation position multiplier (<=0=filter)
input double InpSweepHighPosMultMin = 0.0; // Sweep最终仓位倍数达到该值时降权(0=禁用)
input double InpSweepHighPosMultMult = 1.0; // Sweep高仓位倍数降权(<=0=过滤)
input double InpAlignedNoContSpreadRiskMax = 0.0; // H1对齐但非延续且spread/risk低于该值时降权(0=禁用)
input double InpAlignedNoContMult = 1.0; // H1对齐非延续低spread/risk仓位倍数(<=0=过滤)
input double InpSellSpreadRiskMin = 0.0; // Sell入场spread/risk下限(0=禁用)
input double InpSellSpreadRiskMax = 0.0; // Sell入场spread/risk上限(<=min=禁用)
input double InpSellSpreadRiskMult = 1.0; // Sell指定spread/risk区间仓位倍数(<=0=过滤)
input double InpSellSpreadRiskUntilProfitPct = 0.0; // 月内盈利达到该百分比后停止SellSpreadRisk过滤(0=一直启用)
input bool   InpSellSpreadRiskOBOnly = false; // SellSpreadRisk仅作用普通OB, 不影响Sweep
input double InpSmallRiskATRMax = 0.0; // risk/ATR低于该值时降权(0=禁用)
input double InpSmallRiskATRMult = 1.0; // 小risk/ATR仓位倍数(<=0=过滤)
input int    InpSmallRiskATREntryCountMax = 0; // 仅当OB已入场次数小于该值时启用(0=不限)
input int    InpSmallRiskATRAgeMaxBars = 0; // 仅当OB年龄小于该bar数时启用(0=不限)
input double InpRiskATRBandBadMax = 0.0; // risk/ATR低于该值且满足坏簇条件时降权(0=禁用)
input double InpRiskATRBandBadSpreadRiskMax = 0.0; // 坏簇spread/risk上限(0=不限)
input int    InpRiskATRBandBadAgeMinBars = 0; // 坏簇OB最小年龄bars(0=不限)
input int    InpRiskATRBandBadTouchMin = 0; // 坏簇OB最小touch_count(0=不限)
input double InpRiskATRBandBadMult = 1.0; // 坏簇仓位倍数(<=0=过滤)
input bool   InpRiskATRBandBadRequireCounterPush = false; // 坏簇需小周期反向净推进确认
input double InpRiskATRBandGoodMin = 0.0; // risk/ATR不低于该值时视为宽风险趋势单(0=禁用)
input int    InpRiskATRBandGoodTouchMin = 0; // 好簇OB最小touch_count(0=不限)
input double InpRiskATRBandGoodMult = 1.0; // 好簇仓位倍数(<=0=过滤)
input int    InpOldHighScoreOBAgeMinBars = 0; // 老化高分OB最小年龄bars(0=禁用)
input int    InpOldHighScoreOBScoreMin = 0; // 老化高分OB最低评分(0=禁用)
input double InpOldHighScoreOBMult = 1.0; // 老化高分OB仓位倍数(<=0=过滤)
input int    InpOldPosMultOBAgeMinBars = 0; // 老化且高仓位倍数OB最小年龄bars(0=禁用)
input double InpOldPosMultOBPosMin = 0.0; // 老化OB最低仓位倍数(0=禁用)
input double InpOldPosMultOBMult = 1.0; // 老化高仓位OB仓位倍数(<=0=过滤)
input double InpDeepConfirmLowSpreadConfirmMax = 0.0; // 深确认低spread/risk确认位置上限(0=禁用)
input double InpDeepConfirmLowSpreadRiskMax = 0.0; // 深确认低spread/risk上限(0=禁用)
input double InpDeepConfirmLowSpreadMult = 1.0; // 深确认低spread/risk仓位倍数(<=0=过滤)
input int    InpBuyContNoH1AgeMinBars = 0; // Buy延续非H1老化OB最小年龄bars(0=禁用)
input double InpBuyContNoH1SpreadRiskMax = 0.0; // Buy延续非H1老化OB spread/risk上限(0=不限)
input double InpBuyContNoH1AgeMult = 1.0; // Buy延续非H1老化OB仓位倍数(<=0=过滤)
input bool   InpBOSLockAllowCounterMomentum = false; // BOS方向锁下允许逆H4但小周期强延续的bounce
input int    InpBOSLockCounterMomentumTF = 5; // BOS方向锁逆向放行观察周期(分钟)
input int    InpBOSLockCounterMomentumBars = 3; // BOS方向锁逆向放行观察bar数
input double InpBOSLockCounterMomentumMinATR = 0.45; // BOS方向锁逆向放行同向实体净推进/ATR阈值
input bool   InpBOSLockAllowCounterBreak = false; // BOS方向锁下允许逆H4小周期结构突破+动能延续
input int    InpBOSLockCounterBreakTF = 5; // 逆H4结构突破观察周期(分钟)
input int    InpBOSLockCounterBreakBars = 3; // 逆H4结构突破动能观察bar数
input double InpBOSLockCounterBreakMinATR = 0.35; // 逆H4结构突破同向实体净推进/ATR阈值
input double InpBOSLockCounterBreakBufferATR = 0.03; // 逆H4结构突破缓冲/ATR
input bool   InpBOSLockCounterBreakOBOnly = false; // 逆H4结构突破放行仅限普通OB, 不放行Sweep
input bool   InpBOSLockAllowCounterOB = false; // BOS方向锁下允许逆H4普通OB反转结构, 不放行Sweep
input bool   InpBOSLockAllowCounterBounce = false; // BOS方向锁下允许逆H4成熟反弹bounce
input int    InpBOSLockCounterBounceSecMin = 0; // BOS方向锁逆向放行最小反弹确认秒数(0=不限)
input int    InpBOSLockCounterBounceSecMax = 0; // BOS方向锁逆向放行最大反弹确认秒数(0=禁用)
input int    InpSweepBadAgeMinBars = 0;     // Sweep zone age bad-cluster min bars (inclusive; 0=disabled)
input int    InpSweepBadAgeMaxBars = 0;     // Sweep zone age bad-cluster max bars (exclusive; <=min=disabled)
input double InpSweepBadAgeMult = 1.0;      // Sweep bad-age position multiplier (<=0=filter)
input double InpOBPosMult       = 1.0;      // regular OB position multiplier; does not affect sweep/range/HTFPB
input double InpOBPosMultMinBalance = 0.0;  // minimum balance before OB position multiplier is active
input double InpOBMinPosMult    = 0.0;      // 普通OB最终仓位倍数低于该值则过滤(0=禁用)
input string InpOBMinPosMultDirections = ""; // 普通OB低仓位过滤方向: BUY,SELL; 空=全部方向
input bool   InpOBMinPosMultOnlyMonthlyNonNegative = false; // 仅月内未亏损时启用低仓位OB过滤
input double InpOBHighPosBoostMin = 0.0;    // 普通OB最终仓位倍数达到该值时放大(0=禁用)
input double InpOBHighPosBoostMult = 1.0;   // 普通OB高仓位倍数放大倍数(1=不变, <=0=过滤)
input string InpOBHighPosBoostDirections = ""; // 普通OB高仓位放大方向: BUY,SELL; 空=全部方向
input double InpOBNoH1PosMult   = 1.0;      // 普通OB非H1对齐仓位倍数(<=0=过滤)
input double InpOBMonthlyWarmupProfitPct = 0.0; // 普通OB达到月内利润前降仓(0=禁用)
input double InpOBMonthlyWarmupPosMult = 1.0;   // 普通OB月内warmup仓位倍数(<=0=过滤)
input double InpOBMonthlyProfitCapPct = 0.0;    // 普通OB月内利润达到该百分比后降仓(0=禁用)
input double InpOBMonthlyProfitCapMult = 1.0;   // 普通OB月内利润达标后仓位倍数(<=0=过滤)
input double InpOBMonthlyNegativePosMult = 1.0; // 普通OB月内转负后仓位倍数(<=0=过滤)
input double InpOBMonthlyMultMaxStartBalance = 0.0; // 普通OB月内乘数最大月初余额(0=不限)
input string InpOBBadHours       = "";       // 鏅€歄B寮卞皬鏃禖SV(涓嶅奖鍝峉weep/鍖洪棿绐佺牬)
input double InpOBBadHourMult    = 1.0;      // 鏅€歄B寮卞皬鏃朵粨浣嶅€嶆暟(<=0杩囨护)
input string InpLowBalanceOBBadHours = "";  // 浣庝綑棰濇櫘閫歄B寮卞皬鏃禖SV
input string InpLowBalanceOBBadMonths = ""; // 浣庝綑棰濇櫘閫歄B寮辨湀浠紺SV(绌?鍏ㄩ儴鏈堜唤)
input double InpLowBalanceOBBadMaxMonthStartBalance = 0.0; // 鏈堝垵浣欓涓嶉珮浜庤鍊兼椂鍚敤(0=绂佺敤)
input double InpLowBalanceOBBadHourMult = 1.0; // 浣庝綑棰濇櫘閫歄B寮卞皬鏃朵粨浣嶅€嶆暟(<=0杩囨护)
input double InpLowBalanceThreshold = 0.0;   // 浣欓浣庝簬璇ュ€煎惎鐢ㄥ惎鍔ㄦ湡淇濇姢(0=绂佺敤)
input double InpLowBalancePosMult = 1.0;     // 鍚姩鏈熶粨浣嶅€嶆暟
input double InpLowBalanceMaxLotSize = 0.0;  // 鍚姩鏈熸渶澶ф墜鏁?0=涓嶉檺鍒?
input double InpMonthlyGuardMinBalance = 0.0; // 浣欓杈惧埌璇ュ€煎悗鎵嶅惎鐢ㄦ湀鍐呴鎺?0=濮嬬粓鍚敤)
input int    InpMonthlyMaxEntries = 0;      // 月内最多新开仓次数(0=不限制)
input double InpMonthlyLossStopPct = 0.0;    // 鏈堝唴浣欓鍥炴挙瓒呰繃璇ョ櫨鍒嗘瘮鍚庡仠姝㈡柊寮€浠?0=绂佺敤)
input int    InpMonthlyLossStopMinTrades = 0; // 鏈堜簭鍋滄鍓嶈嚦灏戝厑璁哥殑鏈堝唴寮€浠撴暟(0=杈惧埌鍗冲仠)
input int    InpMonthlyEarlyLossStopTrades = 0; // 鏈堝垵绗琋绗斿悗妫€鏌ヤ竴娆″急鏈堢啍鏂?0=绂佺敤)
input double InpMonthlyEarlyLossStopPct = 0.0;  // 鏈堝垵寮辨湀鐔旀柇浜忔崯鐧惧垎姣?
input double InpMonthlyEarlyLossStopMinBalance = 0.0; // 鏈堝垵寮辨湀鐔旀柇鍚敤浣欓(0=濮嬬粓鍚敤)
input double InpMonthlyNegativePosMult = 1.0; // 鏈堝唴浣欓浣庝簬鏈堝垵鏃朵粨浣嶅€嶆暟
input bool   InpMonthlyEarlyLossStopContinuous = false; // true=绗琋绗斿悗鎸佺画妫€鏌ュ急鏈堢啍鏂紝false=鍙湪绗琋绗旀鏌?
input double InpMonthlyWarmupProfitPct = 0.0; // month profit pct required before full size (0=disabled)
input double InpMonthlyWarmupPosMult = 1.0;   // position multiplier before monthly warmup profit is reached
input double InpMonthlyDefensiveLossPct = 0.0; // 月内亏损达到月初余额该百分比后启用防守时段(0=禁用)
input double InpMonthlyDefensiveUntilProfitPct = 0.0; // 月内盈利达到月初余额该百分比前启用防守时段(0=禁用)
input double InpMonthlyDefensiveMaxMonthStartBalance = 0.0; // 月初余额不高于该值时才启用防守(0=不限制)
input int    InpMonthlyDefensiveMinTrades = 0; // 月内防守模式至少交易笔数
input string InpMonthlyDefensiveNoEntryHours = ""; // 月内防守模式禁入小时CSV
input string InpMonthlyDefensiveNoBuyHours = "";   // 月内防守模式禁多小时CSV
input string InpMonthlyDefensiveNoSellHours = "";  // 月内防守模式禁空小时CSV
input double InpMonthlyDefensivePosMult = 1.0; // 月内防守模式仓位倍数(<=0过滤)
input double InpMonthlyProfitLockMinBalance = 0.0; // 浣欓杈惧埌璇ュ€煎悗鍚敤鏈堝唴鐩堝埄鍥炲悙閿?0=濮嬬粓鍚敤)
input double InpMonthlyProfitLockStartPct = 0.0; // 鏈堝唴鐩堝埄杈惧埌鏈堝垵浣欓鐧惧垎姣斿悗鍚敤鍥炲悙閿?0=绂佺敤)
input double InpMonthlyProfitLockKeepPct = 0.0;  // 鍥炲悙鍒板嘲鍊肩泩鍒╃殑璇ョ櫨鍒嗘瘮浠ヤ笅鍋滄鏂板紑浠?
input double InpMonthlyProfitTargetStopPct = 0.0; // 鏈堝唴杈惧埌鐩堝埄鐩爣鍚庡仠姝㈡柊鍏ュ満(%鏈堝垵浣欓,0=绂佺敤)
input double InpMonthlyProfitTargetStopMinBalance = 0.0; // 鏈堝垵浣欓涓嶄綆浜庤鍊兼椂鍚敤鐩堝埄鐩爣鍋滄墜(0=涓嶉檺)
input double InpMonthlyProfitTargetStopMaxBalance = 0.0; // 鏈堝垵浣欓涓嶉珮浜庤鍊兼椂鍚敤鐩堝埄鐩爣鍋滄墜(0=涓嶉檺)
input string InpMonthlyProfitTargetStopMonths = ""; // 鏈堝害鐩堝埄鐩爣鍋滄墜鏈堜唤CSV(绌?鍏ㄩ儴鏈堜唤)
input double InpMonthlyProfitTargetStop2Pct = 0.0; // 绗簩缁勬湀鍐呯泩鍒╃洰鏍囧仠鎵?%鏈堝垵浣欓,0=绂佺敤)
input double InpMonthlyProfitTargetStop2MinBalance = 0.0; // 绗簩缁勬湀鍒濅綑棰濅笅闄?0=涓嶉檺)
input double InpMonthlyProfitTargetStop2MaxBalance = 0.0; // 绗簩缁勬湀鍒濅綑棰濅笂闄?0=涓嶉檺)
input string InpMonthlyProfitTargetStop2Months = ""; // 绗簩缁勬湀搴︾泩鍒╃洰鏍囧仠鎵嬫湀浠紺SV(绌?鍏ㄩ儴鏈堜唤)
input bool   InpSharedMonthlyGuard = false; // 澶氬浘琛ㄥ叡浜湀搴﹂鎺х姸鎬?榛樿鍏抽棴)
input string InpSharedMonthlyGuardKey = ""; // 鍏变韩鏈堝害椋庢帶Key(鍚岀粍鍚堝繀椤讳竴鑷?
input bool   InpSharedMonthlyGuardDebug = false; // 鎵撳嵃鍏变韩鏈堝害椋庢帶璇婃柇鏃ュ織
input int    InpMaxConcurrent    = 5;        // 鏈€澶у悓鏃舵寔浠撴暟
input double InpFreeRunMinR      = 0.0;      // 娴泩鈮ユR涓嶈骞跺彂(0=绂佺敤)
input int    InpCooldownBars     = 0;        // 寮€浠撳喎鍗?bars)
input string InpEntryMonths      = "";       // 鍏佽鍏ュ満鏈堜唤CSV, 濡?3,11"(绌?鍏ㄩ儴鏈堜唤)
input string InpNoEntryHours     = "";       // 绂佹鍏ュ満灏忔椂CSV, 濡?0,9,12"(绌?绂佺敤)
input string InpNoBuyHours       = "";       // 绂佹鍋氬灏忔椂CSV(绌?绂佺敤)
input string InpNoSellHours      = "";       // 绂佹鍋氱┖灏忔椂CSV(绌?绂佺敤)
input string InpLowRiskHours     = "";       // 浣庝粨浣嶅皬鏃禖SV(绌?绂佺敤)
input double InpLowRiskHourMult  = 1.0;      // 浣庝粨浣嶅皬鏃朵粨浣嶅€嶆暟
input string InpHighRiskHours    = "";       // 楂樹粨浣嶅皬鏃禖SV(绌?绂佺敤)
input double InpHighRiskHourMult = 1.0;      // 楂樹粨浣嶅皬鏃朵粨浣嶅€嶆暟
input string InpContextFilter1Months = "";   // Context filter1 months CSV(empty=all)
input string InpContextFilter1NoHours = "";  // Context filter1 blocked hours CSV
input string InpContextFilter1NoBuyHours = ""; // Context filter1 blocked buy hours CSV
input string InpContextFilter1NoSellHours = ""; // Context filter1 blocked sell hours CSV
input double InpContextFilter1MinMonthStartBalance = 0.0; // Context filter1 month-start min balance
input double InpContextFilter1MaxMonthStartBalance = 0.0; // Context filter1 month-start max balance
input double InpContextFilter1MaxBalance = 0.0; // Context filter1 current balance max(0=不限)
input double InpContextFilter1MinPrice = 0.0; // Context filter1 min current price(0=涓嶉檺)
input double InpContextFilter1MaxPrice = 0.0; // Context filter1 max current price(0=涓嶉檺)
input double InpContextFilter1Mult = 1.0;     // Context filter1 position multiplier(<=0=filter)
input string InpContextFilter2Months = "";   // Context filter2 months CSV(empty=all)
input string InpContextFilter2NoHours = "";  // Context filter2 blocked hours CSV
input string InpContextFilter2NoBuyHours = ""; // Context filter2 blocked buy hours CSV
input string InpContextFilter2NoSellHours = ""; // Context filter2 blocked sell hours CSV
input double InpContextFilter2MinMonthStartBalance = 0.0; // Context filter2 month-start min balance
input double InpContextFilter2MaxMonthStartBalance = 0.0; // Context filter2 month-start max balance
input double InpContextFilter2MaxBalance = 0.0; // Context filter2 current balance max(0=不限)
input double InpContextFilter2MinPrice = 0.0; // Context filter2 min current price(0=涓嶉檺)
input double InpContextFilter2MaxPrice = 0.0; // Context filter2 max current price(0=涓嶉檺)
input double InpContextFilter2Mult = 1.0;     // Context filter2 position multiplier(<=0=filter)
input string InpContextFilter3Months = "";   // Context filter3 months CSV(empty=all)
input string InpContextFilter3NoHours = "";  // Context filter3 blocked hours CSV
input string InpContextFilter3NoBuyHours = ""; // Context filter3 blocked buy hours CSV
input string InpContextFilter3NoSellHours = ""; // Context filter3 blocked sell hours CSV
input double InpContextFilter3MinMonthStartBalance = 0.0; // Context filter3 month-start min balance
input double InpContextFilter3MaxMonthStartBalance = 0.0; // Context filter3 month-start max balance
input double InpContextFilter3MaxBalance = 0.0; // Context filter3 current balance max(0=不限)
input double InpContextFilter3MinPrice = 0.0; // Context filter3 min current price(0=涓嶉檺)
input double InpContextFilter3MaxPrice = 0.0; // Context filter3 max current price(0=涓嶉檺)
input double InpContextFilter3Mult = 1.0;     // Context filter3 position multiplier(<=0=filter)
input string InpContextFilter4Months = "";   // Context filter4 months CSV(empty=all)
input string InpContextFilter4NoHours = "";  // Context filter4 blocked hours CSV
input string InpContextFilter4NoBuyHours = ""; // Context filter4 blocked buy hours CSV
input string InpContextFilter4NoSellHours = ""; // Context filter4 blocked sell hours CSV
input double InpContextFilter4MinMonthStartBalance = 0.0; // Context filter4 month-start min balance
input double InpContextFilter4MaxMonthStartBalance = 0.0; // Context filter4 month-start max balance
input double InpContextFilter4MaxBalance = 0.0; // Context filter4 current balance max(0=不限)
input double InpContextFilter4MinPrice = 0.0; // Context filter4 min current price(0=涓嶉檺)
input double InpContextFilter4MaxPrice = 0.0; // Context filter4 max current price(0=涓嶉檺)
input double InpContextFilter4Mult = 1.0;     // Context filter4 position multiplier(<=0=filter)
input string InpContextFilter5Months = "";   // Context filter5 months CSV(empty=all)
input string InpContextFilter5NoHours = "";  // Context filter5 blocked hours CSV
input string InpContextFilter5NoBuyHours = ""; // Context filter5 blocked buy hours CSV
input string InpContextFilter5NoSellHours = ""; // Context filter5 blocked sell hours CSV
input double InpContextFilter5MinMonthStartBalance = 0.0; // Context filter5 month-start min balance
input double InpContextFilter5MaxMonthStartBalance = 0.0; // Context filter5 month-start max balance
input double InpContextFilter5MaxBalance = 0.0; // Context filter5 current balance max(0=不限)
input double InpContextFilter5MinPrice = 0.0; // Context filter5 min current price(0=涓嶉檺)
input double InpContextFilter5MaxPrice = 0.0; // Context filter5 max current price(0=涓嶉檺)
input double InpContextFilter5Mult = 1.0;     // Context filter5 position multiplier(<=0=filter)
input string InpContextReverseHours = "";     // 涓婁笅鏂囧弽鍚戝叆鍦哄皬鏃禖SV(绌?绂佺敤)
input string InpContextReverseDirections = ""; // 涓婁笅鏂囧弽鍚戞柟鍚慍SV(buy/sell,绌?涓嶉檺)
input int    InpContextReverseSellEarlyDayMax = 0; // SELL鍙嶅悜浠呴檺鏈堝垵<=N鏃?0=涓嶉檺)
input int    InpContextReverseSellLateDayMin = 0;  // SELL鍙嶅悜浠呴檺鏈堟湯>=N鏃?0=涓嶉檺)
input double InpContextReverseMinPrice = 0.0; // 涓婁笅鏂囧弽鍚戞渶灏忓綋鍓嶄环鏍?0=涓嶉檺)
input double InpContextReverseMaxPrice = 0.0; // 涓婁笅鏂囧弽鍚戞渶澶у綋鍓嶄环鏍?0=涓嶉檺)
input double InpContextReverseMaxMonthStartBalance = 0.0; // 鏈堝垵浣欓涓嶉珮浜庤鍊兼椂鍚敤(0=涓嶉檺)
input double InpContextReverseRiskMult = 1.0; // 鍙嶅悜鍏ュ満SL璺濈=鍘熷risk鍊嶆暟
input double InpContextReverseMaxRisk = 0.0;  // 涓婁笅鏂囧弽鍚戞渶澶у師濮媟isk浠锋牸璺濈(0=涓嶉檺)
input double InpContextReverseTPR = 1.0;      // 鍙嶅悜鍏ュ満鍥哄畾TP R(0=鏃燭P)
input double InpContextBEMinPrice = 0.0;      // 涓婁笅鏂嘊E鏈€灏忓叆鍦轰环(0=绂佺敤)
input double InpContextBEMaxPrice = 0.0;      // 涓婁笅鏂嘊E鏈€澶у叆鍦轰环(0=涓嶉檺)
input double InpContextBEMaxMonthStartBalance = 0.0; // 鏈堝垵浣欓涓嶉珮浜庤鍊兼椂鍚敤(0=涓嶉檺)
input double InpContextBER = 0.0;             // 涓婁笅鏂嘊E瑙﹀彂R(0=绂佺敤)
input double InpContextBELockR = 0.0;         // 涓婁笅鏂嘊E閿佸畾R
input int    InpEarlyBounceSecMax = 0;        // Bounce纭杩囧揩涓婇檺(0=绂佺敤)
input double InpEarlyBounceMult = 1.0;        // 杩囧揩纭浠撲綅鍊嶆暟(<=0杩囨护)
input int    InpLateBounceSec    = 0;        // Bounce纭瓒呰繃N绉掑悗闄嶆潈(0=绂佺敤)
input double InpLateBounceMult   = 1.0;      // 鏅氱‘璁や粨浣嶅€嶆暟
input double InpBounceSweetMinPct = 0.0;     // Bounce鐢滅偣涓嬮檺(OB楂樺害姣斾緥,0=绂佺敤)
input double InpBounceSweetMaxPct = 0.0;     // Bounce鐢滅偣涓婇檺(OB楂樺害姣斾緥,0=绂佺敤)
input double InpOutsideBounceSweetMult = 1.0; // 闈濨ounce鐢滅偣浠撲綅鍊嶆暟
input double InpBadBounceMinPct  = 0.0;      // Bounce坏区间下限(OB高度比例,0=禁用)
input double InpBadBounceMaxPct  = 0.0;      // Bounce坏区间上限(<=min=禁用)
input double InpBadBounceMult    = 1.0;      // Bounce坏区间仓位倍数(<=0=过滤)
input string InpBadBounceSignalTypes = "";   // Bounce坏区间作用信号族(all/ob/sweep/bos...)
input double InpBadBounceMaxEntryPosMult = 0.0; // Bounce坏区间仅作用于入场仓位倍数不高于该值的样本(0=不限)
input string InpBadBouncePosMultDirections = ""; // Bounce坏区间入场仓位限制作用方向: BUY,SELL; 空=全部方向
input double InpBadRiskMin       = 0.0;      // 寮遍闄╁尯闂翠笅闄?浠锋牸璺濈,0=绂佺敤)
input double InpBadRiskMax       = 0.0;      // 寮遍闄╁尯闂翠笂闄?浠锋牸璺濈,0=绂佺敤)
input double InpBadRiskMult      = 1.0;      // 寮遍闄╁尯闂翠粨浣嶅€嶆暟
input double InpLargeRiskMin     = 0.0;      // 澶ч闄╃粨鏋勪笅闄?浠锋牸璺濈,0=绂佺敤)
input double InpLargeRiskMult    = 1.0;      // 澶ч闄╃粨鏋勪粨浣嶅€嶆暟
input double InpShallowConfirmPosMin = -999.0; // 纭浣嶇疆杩囨祬闃堝€?confirm_ob_pos,<=-999绂佺敤)
input double InpShallowConfirmPosMult = 1.0; // 纭浣嶇疆杩囨祬浠撲綅鍊嶆暟(<=0杩囨护)
input string InpShallowConfirmSignalTypes = ""; // 浅确认限制作用信号族(all/ob/sweep/bos...)
input string InpShallowConfirmDirections = ""; // 浅确认限制作用方向: BUY,SELL; 空=全部方向
input double InpShallowConfirmMaxEntryPosMult = 0.0; // 浅确认限制仅作用于入场仓位倍数不高于该值的样本(0=不限)
input double InpDeepFastConfirmPosMax = 999.0; // 深确认过深阈值(confirm_ob_pos,>=999禁用)
input int    InpDeepFastConfirmSecMax = 0; // 深确认过快上限秒数(0=禁用)
input double InpDeepFastConfirmMult = 1.0; // 深确认过深且过快仓位倍数(<=0过滤)
input double InpDeepFastConfirmBounceMinPct = 0.0; // 深快确认坏几何下限(0=不限制)
input double InpDeepFastConfirmBounceMaxPct = 0.0; // 深快确认坏几何上限(<=min=不限制)
input string InpDeepFastConfirmSignalTypes = ""; // 深快确认限制作用信号族(all/ob/sweep/bos...)
input string InpDeepFastConfirmDirections = ""; // 深快确认限制作用方向: BUY,SELL; 空=全部方向
input double InpBadClusterMinBalance = 0.0;  // 浣欓杈惧埌璇ュ€煎悗鎵嶅惎鐢ㄧ粍鍚堝潖绨囬檷鏉?0=濮嬬粓鍚敤)
input bool   InpBadClusterOnlyMonthlyNegative = false; // 浠呮湀鍐呬綑棰濅綆浜庢湀鍒濇椂鍚敤缁勫悎鍧忕皣闄嶆潈
input string InpBadCluster1Hours = "";       // 缁勫悎鍧忕皣1灏忔椂CSV(绌?绂佺敤)
input double InpBadCluster1RiskMin = 0.0;    // 缁勫悎鍧忕皣1椋庨櫓涓嬮檺
input double InpBadCluster1RiskMax = 0.0;    // 缁勫悎鍧忕皣1椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpBadCluster1ConfirmMin = -999.0; // 缁勫悎鍧忕皣1纭浣嶇疆涓嬮檺
input double InpBadCluster1ConfirmMax = 999.0;  // 缁勫悎鍧忕皣1纭浣嶇疆涓婇檺
input double InpBadCluster1Mult = 1.0;       // 缁勫悎鍧忕皣1浠撲綅鍊嶆暟(<=0杩囨护)
input string InpBadCluster1Signal = "";      // 缁勫悎鍧忕皣1淇″彿绫诲瀷(all/ob/sweep/range)
input string InpBadCluster2Hours = "";       // 缁勫悎鍧忕皣2灏忔椂CSV(绌?绂佺敤)
input double InpBadCluster2RiskMin = 0.0;    // 缁勫悎鍧忕皣2椋庨櫓涓嬮檺
input double InpBadCluster2RiskMax = 0.0;    // 缁勫悎鍧忕皣2椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpBadCluster2ConfirmMin = -999.0; // 缁勫悎鍧忕皣2纭浣嶇疆涓嬮檺
input double InpBadCluster2ConfirmMax = 999.0;  // 缁勫悎鍧忕皣2纭浣嶇疆涓婇檺
input double InpBadCluster2Mult = 1.0;       // 缁勫悎鍧忕皣2浠撲綅鍊嶆暟(<=0杩囨护)
input string InpBadCluster2Signal = "";      // 缁勫悎鍧忕皣2淇″彿绫诲瀷(all/ob/sweep/range)
input string InpBadCluster3Hours = "";       // 缁勫悎鍧忕皣3灏忔椂CSV(绌?绂佺敤)
input double InpBadCluster3RiskMin = 0.0;    // 缁勫悎鍧忕皣3椋庨櫓涓嬮檺
input double InpBadCluster3RiskMax = 0.0;    // 缁勫悎鍧忕皣3椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpBadCluster3ConfirmMin = -999.0; // 缁勫悎鍧忕皣3纭浣嶇疆涓嬮檺
input double InpBadCluster3ConfirmMax = 999.0;  // 缁勫悎鍧忕皣3纭浣嶇疆涓婇檺
input double InpBadCluster3Mult = 1.0;       // 缁勫悎鍧忕皣3浠撲綅鍊嶆暟(<=0杩囨护)
input string InpBadCluster3Signal = "";      // 缁勫悎鍧忕皣3淇″彿绫诲瀷(all/ob/sweep/range)
input string InpBadCluster4Hours = "";       // 缁勫悎鍧忕皣4灏忔椂CSV(绌?绂佺敤)
input double InpBadCluster4RiskMin = 0.0;    // 缁勫悎鍧忕皣4椋庨櫓涓嬮檺
input double InpBadCluster4RiskMax = 0.0;    // 缁勫悎鍧忕皣4椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpBadCluster4ConfirmMin = -999.0; // 缁勫悎鍧忕皣4纭浣嶇疆涓嬮檺
input double InpBadCluster4ConfirmMax = 999.0;  // 缁勫悎鍧忕皣4纭浣嶇疆涓婇檺
input double InpBadCluster4Mult = 1.0;       // 缁勫悎鍧忕皣4浠撲綅鍊嶆暟(<=0杩囨护)
input string InpBadCluster4Signal = "";      // 缁勫悎鍧忕皣4淇″彿绫诲瀷(all/ob/sweep/range)
input string InpBadCluster5Hours = "";       // 缁勫悎鍧忕皣5灏忔椂CSV(绌?绂佺敤)
input double InpBadCluster5RiskMin = 0.0;    // 缁勫悎鍧忕皣5椋庨櫓涓嬮檺
input double InpBadCluster5RiskMax = 0.0;    // 缁勫悎鍧忕皣5椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpBadCluster5ConfirmMin = -999.0; // 缁勫悎鍧忕皣5纭浣嶇疆涓嬮檺
input double InpBadCluster5ConfirmMax = 999.0;  // 缁勫悎鍧忕皣5纭浣嶇疆涓婇檺
input double InpBadCluster5Mult = 1.0;       // 缁勫悎鍧忕皣5浠撲綅鍊嶆暟(<=0杩囨护)
input string InpBadCluster5Signal = "";      // 缁勫悎鍧忕皣5淇″彿绫诲瀷(all/ob/sweep/range)
input string InpBadCluster6Hours = "";       // 缁勫悎鍧忕皣6灏忔椂CSV(绌?绂佺敤)
input double InpBadCluster6RiskMin = 0.0;    // 缁勫悎鍧忕皣6椋庨櫓涓嬮檺
input double InpBadCluster6RiskMax = 0.0;    // 缁勫悎鍧忕皣6椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpBadCluster6ConfirmMin = -999.0; // 缁勫悎鍧忕皣6纭浣嶇疆涓嬮檺
input double InpBadCluster6ConfirmMax = 999.0;  // 缁勫悎鍧忕皣6纭浣嶇疆涓婇檺
input double InpBadCluster6Mult = 1.0;       // 缁勫悎鍧忕皣6浠撲綅鍊嶆暟(<=0杩囨护)
input string InpBadCluster6Signal = "";      // 缁勫悎鍧忕皣6淇″彿绫诲瀷(all/ob/sweep/range)
input bool   InpBadClusterFilteredMonthlyStop = false; // 鍧忕皣杩囨护淇″彿鍚庨攣浣忔湰鏈堟柊鍏ュ満
input double InpBadClusterFilteredStopMinBalance = 0.0; // 鍧忕皣杩囨护鍋滄墜鍚敤浣欓/宄板€?0=濮嬬粓鍚敤)
input double InpStartupBadClusterMaxMonthStartBalance = 0.0; // 鍚姩鏈熷潖绨囦粎鍦ㄦ湀鍒濅綑棰?=璇ュ€兼椂鍚敤(0=绂佺敤)
input string InpStartupBadCluster1Hours = "";       // 鍚姩鏈熷潖绨?灏忔椂CSV(绌?绂佺敤)
input double InpStartupBadCluster1RiskMin = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓嬮檺
input double InpStartupBadCluster1RiskMax = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpStartupBadCluster1ConfirmMin = -999.0; // 鍚姩鏈熷潖绨?纭浣嶇疆涓嬮檺
input double InpStartupBadCluster1ConfirmMax = 999.0;  // 鍚姩鏈熷潖绨?纭浣嶇疆涓婇檺
input double InpStartupBadCluster1Mult = 1.0;       // 鍚姩鏈熷潖绨?浠撲綅鍊嶆暟(<=0杩囨护)
input string InpStartupBadCluster1Signal = "";      // 鍚姩鏈熷潖绨?淇″彿绫诲瀷(all/ob/sweep/range)
input string InpStartupBadCluster2Hours = "";       // 鍚姩鏈熷潖绨?灏忔椂CSV(绌?绂佺敤)
input double InpStartupBadCluster2RiskMin = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓嬮檺
input double InpStartupBadCluster2RiskMax = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpStartupBadCluster2ConfirmMin = -999.0; // 鍚姩鏈熷潖绨?纭浣嶇疆涓嬮檺
input double InpStartupBadCluster2ConfirmMax = 999.0;  // 鍚姩鏈熷潖绨?纭浣嶇疆涓婇檺
input double InpStartupBadCluster2Mult = 1.0;       // 鍚姩鏈熷潖绨?浠撲綅鍊嶆暟(<=0杩囨护)
input string InpStartupBadCluster2Signal = "";      // 鍚姩鏈熷潖绨?淇″彿绫诲瀷(all/ob/sweep/range)
input string InpStartupBadCluster3Hours = "";       // 鍚姩鏈熷潖绨?灏忔椂CSV(绌?绂佺敤)
input double InpStartupBadCluster3RiskMin = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓嬮檺
input double InpStartupBadCluster3RiskMax = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpStartupBadCluster3ConfirmMin = -999.0; // 鍚姩鏈熷潖绨?纭浣嶇疆涓嬮檺
input double InpStartupBadCluster3ConfirmMax = 999.0;  // 鍚姩鏈熷潖绨?纭浣嶇疆涓婇檺
input double InpStartupBadCluster3Mult = 1.0;       // 鍚姩鏈熷潖绨?浠撲綅鍊嶆暟(<=0杩囨护)
input string InpStartupBadCluster3Signal = "";      // 鍚姩鏈熷潖绨?淇″彿绫诲瀷(all/ob/sweep/range)
input string InpStartupBadCluster4Hours = "";       // 鍚姩鏈熷潖绨?灏忔椂CSV(绌?绂佺敤)
input double InpStartupBadCluster4RiskMin = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓嬮檺
input double InpStartupBadCluster4RiskMax = 0.0;    // 鍚姩鏈熷潖绨?椋庨櫓涓婇檺(<=min=绂佺敤椋庨櫓鏉′欢)
input double InpStartupBadCluster4ConfirmMin = -999.0; // 鍚姩鏈熷潖绨?纭浣嶇疆涓嬮檺
input double InpStartupBadCluster4ConfirmMax = 999.0;  // 鍚姩鏈熷潖绨?纭浣嶇疆涓婇檺
input double InpStartupBadCluster4Mult = 1.0;       // 鍚姩鏈熷潖绨?浠撲綅鍊嶆暟(<=0杩囨护)
input string InpStartupBadCluster4Signal = "";      // 鍚姩鏈熷潖绨?淇″彿绫诲瀷(all/ob/sweep/range)
input bool   InpEnableHTFNetPushFilter = false; // 鍚敤HTF鍑€鎺ㄨ繘浠撲綅杩囨护
input int    InpHTFNetPushTF     = 15;       // HTF鍑€鎺ㄨ繘鍛ㄦ湡(鍒嗛挓)
input int    InpHTFNetPushBars   = 4;        // HTF鍑€鎺ㄨ繘瑙傚療闂悎K鏁?
input double InpHTFNetPushMinATR = 0.50;     // 鍑€鎺ㄨ繘闃堝€?ATR鍊嶆暟,<=0绂佺敤)
input double InpHTFNetPushAlignedMult = 1.0; // HTF鍚屽悜鍑€鎺ㄨ繘浠撲綅鍊嶆暟
input double InpHTFNetPushNeutralMult = 1.0; // HTF鏃犳槑鏄惧噣鎺ㄨ繘浠撲綅鍊嶆暟
input double InpHTFNetPushCounterMult = 1.0; // HTF鍙嶅悜鍑€鎺ㄨ繘浠撲綅鍊嶆暟(<=0杩囨护)
input bool   InpEnableHTFPullback = false; // 鍚敤HTF鍑€鎺ㄨ繘鍚庣殑鍥炶俯鍖轰俊鍙?
input bool   InpHTFPullbackOnly = false;   // 浠呬氦鏄揌TF鍥炶俯鍖轰俊鍙?
input int    InpHTFPullbackTF = 15;        // HTF鍥炶俯淇″彿鍛ㄦ湡(鍒嗛挓)
input int    InpHTFPullbackBars = 3;       // HTF鍑€鎺ㄨ繘瑙傚療闂悎K鏁?
input double InpHTFPullbackMinATR = 0.80;  // HTF鍑€鎺ㄨ繘闃堝€?ATR鍊嶆暟)
input double InpHTFPullbackZoneATR = 0.35; // 鍥炶俯鍖洪珮搴?ATR鍊嶆暟)
input double InpHTFPullbackOffsetATR = 0.10; // 鎺ㄨ繘鏀剁洏浠峰埌鍥炶俯鍖鸿繎绔亸绉?ATR鍊嶆暟)
input double InpHTFPullbackTPMult = 1.0;   // TP=HTF鍥炶俯鍖洪珮搴﹀€嶆暟(0=DTP)
// ── HTF Range Fade: 大周期震荡区间高抛低吸 ──────────────────────────
input bool   InpEnableRangeFade = false;        // 启用震荡区间高抛低吸(HTF区间+LTF入场)
input int    InpRangeTF = 240;                  // 区间检测周期(分钟,H4=240,D1=1440)
input int    InpRangeLookback = 120;            // 区间回溯bar数(H4 40天)
input int    InpRangeMinBars = 24;              // 最小区间形成bar数
input double InpRangeMinWidthATR = 1.5;         // 最小区间宽度(ATR)
input double InpRangeMaxWidthATR = 5.0;         // 最大区间宽度(ATR,过宽=趋势)
input double InpRangeBoundaryToleranceATR = 0.15; // 边界容忍度(ATR,用于swing聚类)
input int    InpRangeSwingStrength = 3;         // swing确认强度(H4用3=12bar确认)
input int    InpRangeMinTouches = 2;            // 边界最少测试次数
input double InpRangeMinContainment = 0.75;     // 价格在区间内最低比例
input double InpRangeEntryZoneATR = 0.30;       // 入场区域(距边界多少ATR触发fade)
input double InpRangeSLBufferATR = 0.50;        // 区间外SL缓冲(ATR)
input int    InpRangeTPTarget = 1;              // TP目标(0=对侧边界,1=中轴)
input double InpRangePosMult = 0.5;             // 区间入场仓位乘数(0=禁用)
input double InpRangeMaxLot = 0.02;             // 区间入场最大手数
input int    InpRangeUpdateBars = 1;            // 区间更新频率(每N根HTF bar)
input bool   InpRangeRequireSweep = true;       // 边界需有sweep才入场
input bool   InpRangeRequireFVG = false;        // 额外要求FVG确认
input bool   InpRangeNoMidTrades = true;        // 区间中部不交易
input double InpBuyMinStrength   = 0.0;      // 鍋氬鏈€浣嶰B寮哄害瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpSellMinStrength  = 0.0;      // 鍋氱┖鏈€浣嶰B寮哄害瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpBuyPosMult       = 1.0;      // 鍋氬浠撲綅涔樻暟瑕嗙洊
input double InpSellPosMult      = 1.0;      // 鍋氱┖浠撲綅涔樻暟瑕嗙洊
input double InpBuyBE_R          = 0.0;      // 鍋氬BE瑙﹀彂瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpBuyBE_Lock       = 0.0;      // 鍋氬BE閿佸畾瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpSellBE_R         = 0.0;      // 鍋氱┖BE瑙﹀彂瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpSellBE_Lock      = 0.0;      // 鍋氱┖BE閿佸畾瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpBuyDTPTriggerR   = 0.0;      // 鍋氬DTP瑙﹀彂瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpBuyDTPRetrace    = 0.0;      // 鍋氬DTP鍥炴挙瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpSellDTPTriggerR  = 0.0;      // 鍋氱┖DTP瑙﹀彂瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input double InpSellDTPRetrace   = 0.0;      // 鍋氱┖DTP鍥炴挙瑕嗙洊(0=鐢ㄤ富鍙傛暟)
input bool   InpEnableStrongAddOn = false;   // 鍚敤寮哄娍寤剁画鍔犱粨
input double InpStrongAddOnTriggerR = 1.0;   // 棣栨鍔犱粨瑙﹀彂娴泩R
input double InpStrongAddOnStepR  = 1.0;     // 鍚庣画姣忔鍔犱粨閫掑R
input int    InpStrongAddOnMaxCount = 0;     // 姣忎釜婧愭寔浠撴渶澶氬姞浠撴鏁?
input double InpStrongAddOnLotMult = 0.5;    // 鍔犱粨鎵嬫暟=婧愭寔浠撳綋鍓嶆墜鏁?鍊嶆暟
input double InpStrongAddOnRiskMult = 0.5;   // 鍔犱粨SL璺濈=婧愭寔浠撳垵濮媟isk*鍊嶆暟
input double InpStrongAddOnMinSpreadRatio = 5.0; // 鍔犱粨鏈€灏弐isk/spread
input bool   InpStrongAddOnUseRiskLot = false; // 加仓按风险百分比重新计算手数
input double InpStrongAddOnRiskPercent = 0.0;  // 加仓风险百分比(0=沿用InpRiskPercent)
input double InpStrongAddOnMaxLotSize = 0.0;   // 加仓最大手数(0=沿用全局)
input string InpStrongAddOnFamilies = "";      // 允许加仓的信号族CSV(空=全部)
input string InpStrongAddOnDirections = "";    // 允许加仓方向CSV(buy/sell, 空=全部)
input int    InpCloseRetryCooldownSec = 0;   // 浜ゆ槗璇锋眰澶辫触鍚庨噸璇曞喎鍗寸鏁?0=涓嶉檺鍒?
input int    InpMaxEntriesPerOB  = 1;        // 姣忎釜OB鏈€澶氬叆鍦烘鏁?1=榛樿涓€娆?
input int    InpOBReentryCooldownMin = 0;    // 鍚屼竴OB鍐嶆鍏ュ満鍐峰嵈鍒嗛挓(0=涓嶉檺鍒?
input double InpReentryPosMult = 1.0;        // 鍚屼竴OB鍐嶆鍏ュ満浠撲綅鍊嶆暟(<=0=杩囨护)
input double InpContinuationPosMult = 1.0;   // 寤剁画OB浠撲綅鍊嶆暟(<=0=杩囨护)
input int    InpFilterContAgeMinBars = 0;    // 杩囨护寤剁画OB鏈€灏忓勾榫刡ars(0=绂佺敤)
input int    InpFilterContAgeMaxBars = 0;    // 杩囨护寤剁画OB鏈€澶у勾榫刡ars(0=绂佺敤)
input bool   InpFilterContNonDeepOnly = false; // 浠呰繃婊ゆ湭娣辫Е鐨勫欢缁璒B
input double InpFilterBuyNoH1MinPosMult = 0.0; // 鍋氬闈濰1闄嶆潈鏈€灏忎粨浣嶄箻鏁?0=绂佺敤)
input double InpFilterBuyNoH1MaxPosMult = 0.0; // 鍋氬闈濰1闄嶆潈鏈€澶т粨浣嶄箻鏁?0=绂佺敤)
input double InpFilterBuyNoH1PosMult = 1.0; // 鍋氬闈濰1楂樹粨浣嶉檷鏉冨€嶆暟(<=0=杩囨护)

// 鈹€鈹€ 澧炲己 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input double InpBoostIn1HOB      = 3.0;      // 1H绾у埆OB鍔犱粨鍊嶆暟
input bool   InpDSWeight         = true;     // 鍚敤渚涢渶鏉冮噸
input double InpDTAddonBoost     = 0.0;      // 浜屾瑙︾棰濆鍔犱粨

// 鈹€鈹€ K绾胯缃?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input int    InpBarTF            = 1;        // 宸ヤ綔鍛ㄦ湡(鍒嗛挓: 1=M1, 5=M5)
input int    InpBars             = 5000;     // 鍔犺浇K绾挎暟
input int    InpOBScanDepth      = 200;      // OB鎵弿娣卞害(bars, 0=鍏ㄩ噺)

// 鈹€鈹€ 鏍囪瘑 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input string InpVersion          = "V96b";   // 绛栫暐鐗堟湰鏍囪瘑
input int    InpMagicNumber      = 202605;   // EA Magic Number

// 鈹€鈹€ v11 鍗曠瓥鐣ュ搧绉峆rofile瑕嗙洊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input bool   InpEnableBTCProfile = false;    // 鍚敤BTC涓撳睘鍙傛暟瑕嗙洊(榛樿鍏抽棴)
input string InpBTCProfileSymbol = "BTC";    // 瑙﹀彂BTC profile鐨勫搧绉嶅悕鐗囨
input double InpBTCBouncePct = 0.25;         // BTC bounce纭姣斾緥
input int    InpBTCTimeoutMin = 120;         // BTC OB杩囨湡鍒嗛挓
input double InpBTCMaxEntryOffsetR = 0.5;    // BTC鏈€澶у叆鍦哄亸绉?
input int    InpBTCBarTF = 5;                // BTC宸ヤ綔鍛ㄦ湡
input bool   InpBTCEnableLiquiditySweep = true; // BTC鍚敤Sweep
input bool   InpBTCLiquiditySweepOnly = false;  // BTC浠匰weep
input int    InpBTCNoOBStartHour = -1;      // BTC绂佹寤篛B寮€濮嬪皬鏃?-1=绂佺敤)
input int    InpBTCNoOBEndHour = -1;        // BTC绂佹寤篛B缁撴潫灏忔椂(-1=绂佺敤)
input double InpBTCSLBufferATR = 1.5;       // BTC SL ATR buffer
input double InpBTCOBHeightTPMult = 1.5;    // BTC OB楂樺害TP
input int    InpBTCTimeExitBars = 80;       // BTC瓒呮椂閫€鍑?
input double InpBTCCapLossR = 0.0;         // BTC 硬损cap R (0=禁用, <0表示loss超过此R则强平)
input string InpBTCCapLossHours = "";        // BTC Cap loss生效小时(空=全天, CSV e.g. "0,1,2,3,4,5")
input string InpBTCCapLossDays = "";          // BTC Cap loss生效星期(空=全部, CSV e.g. "5"=周五)
input int    InpBTCCapLossMinBars = 3;          // BTC Cap loss最短持有bars(低于此不触发,避免入场即被cap)
input int    InpBTCSweepLookbackBars = 12;   // BTC Sweep lookback
input double InpBTCSweepMaxRangeATR = 2.50;  // BTC Sweep range/ATR
input double InpBTCSweepMinRangeSpreadMult = 4.0; // BTC Sweep range/spread
input double InpBTCSweepMinPenetrationATR = 0.05; // BTC Sweep penetration
input double InpBTCSweepMinWickPct = 45.0;   // BTC Sweep wick
input double InpBTCSweepTPMult = 1.0;        // BTC Sweep TP mult
input double InpBTCBreakevenR = 1.0;         // BTC BE瑙﹀彂
input double InpBTCBreakevenLockR = 0.2;     // BTC BE閿佸畾
input double InpBTCDTPTriggerR = 3.0;        // BTC DTP瑙﹀彂
input double InpBTCDTPRetrace = 0.25;        // BTC DTP鍥炴挙
input double InpBTCFixedTPR = 0.0;           // BTC鍥哄畾TP
input bool   InpBTCAllowMonthlyProfitTargetStop = false; // BTC鍏佽鏈堢泩鍒╃洰鏍囧仠姝?
input double InpBTCRiskPercent = 5.4;        // BTC椋庨櫓%
input double InpBTCMaxPosMult = 300.0;       // BTC鏈€澶т粨浣嶄箻鏁?
input double InpBTCMaxLotSize = 9.0;         // BTC鏈€澶ф墜鏁?
input int    InpBTCMaxConcurrent = 8;        // BTC鏈€澶у苟鍙?
input double InpBTCMinRiskSpreadRatio = 5.0; // BTC鏈€灏弐isk/spread
input double InpBTCSweepPosMult = 0.1;       // BTC Sweep浠撲綅鍊嶆暟
input double InpBTCSweepMaxLotSize = 0.01;   // BTC Sweep鏈€澶ф墜鏁?
input double InpBTCLowBalanceThreshold = 1000.0; // BTC浣庝綑棰濋槇鍊?
input double InpBTCLowBalancePosMult = 0.39; // BTC浣庝綑棰濅粨浣嶅€嶆暟
input double InpBTCLowBalanceMaxLotSize = 0.39; // BTC浣庝綑棰濇渶澶ф墜鏁?
input double InpBTCEntryDepthPct = 0.67;     // BTC鍏ュ満娣卞害
input bool   InpBTCEntryDepthFilter = true;  // BTC娣卞害纭繃婊?
input bool   InpBTCRequireDoubleTch = false; // BTC浜岃Е瑕佹眰
input int    InpBTCMaxEntriesPerOB = 4;      // BTC姣廜B鍏ュ満鏁?
input int    InpBTCOBReentryCooldownMin = 30; // BTC鍚孫B鍐峰嵈
input int    InpBTCCooldownBars = 1;         // BTC寮€浠撳喎鍗碽ars
input double InpBTCContinuationPosMult = 1.0; // BTC寤剁画OB鍊嶆暟
input int    InpBTCFilterContAgeMinBars = 0; // BTC寤剁画OB杩囨护鏈€灏忓勾榫?
input int    InpBTCFilterContAgeMaxBars = 0; // BTC寤剁画OB杩囨护鏈€澶у勾榫?
input bool   InpBTCFilterContNonDeepOnly = false; // BTC寤剁画OB浠呰繃婊ら潪娣变綅
input double InpBTCBoostIn1HOB = 2.0;        // BTC 1H OB鍊嶆暟
input int    InpBTCLateBounceSec = 30;       // BTC鏅氱‘璁ょ鏁?
input double InpBTCLateBounceMult = 0.6;     // BTC鏅氱‘璁ゅ€嶆暟
input double InpBTCBounceSweetMinPct = 0.26; // BTC bounce鐢滅偣涓嬮檺
input double InpBTCBounceSweetMaxPct = 0.34; // BTC bounce鐢滅偣涓婇檺
input double InpBTCOutsideBounceSweetMult = 0.7; // BTC闈炵敎鐐瑰€嶆暟
input double InpBTCBadRiskMin = 150.0;       // BTC寮遍闄╀笅闄?
input double InpBTCBadRiskMax = 200.0;       // BTC寮遍闄╀笂闄?
input double InpBTCBadRiskMult = 0.6;        // BTC寮遍闄╁€嶆暟
input double InpBTCLargeRiskMin = 300.0;     // BTC澶ч闄╀笅闄?
input double InpBTCLargeRiskMult = 4.05;     // BTC澶ч闄╁€嶆暟
input string InpBTCNoEntryHours = "0,7,22,23"; // BTC绂佹鍏ュ満灏忔椂
input string InpBTCNoBuyHours = "";         // BTC绂佹鍋氬灏忔椂
input string InpBTCNoSellHours = "17";      // BTC绂佹鍋氱┖灏忔椂
input string InpBTCLowRiskHours = "17";     // BTC浣庝粨浣嶅皬鏃?
input double InpBTCLowRiskHourMult = 0.35;  // BTC浣庝粨浣嶅€嶆暟
input string InpBTCHighRiskHours = "12,13,20,23"; // BTC楂樹粨浣嶅皬鏃?
input double InpBTCHighRiskHourMult = 8.0;  // BTC楂樹粨浣嶅€嶆暟
input bool   InpBTCEnableStateFilter = true; // BTC鍚敤鎬佽繃婊?
input int    InpBTCTrendLookback = 80;       // BTC瓒嬪娍鍥炴函
input int    InpBTCSwingStrength = 3;        // BTC Swing寮哄害
input double InpBTCRangeBE_R = 1.0;          // BTC闇囪崱鎬丅E
input int    InpBTCRangeTimeExit = 20;       // BTC闇囪崱鎬佽秴鏃?
input double InpBTCTrendBE_R = 0.0;          // BTC瓒嬪娍鎬丅E
input double InpBTCTrendBE_Lock = 0.0;       // BTC瓒嬪娍鎬丅E閿佸畾
input double InpBTCTrendDTPRetrace = 0.0;    // BTC瓒嬪娍鎬丏TP鍥炴挙
input bool   InpBTCEnableScoring = true;     // BTC鍚敤璇勫垎
input int    InpBTCMinScore = 0;             // BTC鏈€浣庤瘎鍒?
input double InpBTCProximityATR = 1.0;       // BTC鎺ヨ繎搴TR
input bool   InpBTCEnableDecayExit = true;   // BTC鍚敤琛板噺閫€鍑?
input double InpBTCDecayMinR = 1.0;          // BTC琛板噺鏈€灏廟
input int    InpBTCDecayBars = 3;            // BTC琛板噺bars
input double InpBTCMFEFailMinR = 0.5;        // BTC娴泩澶辫触鏈€灏廟
input double InpBTCMFEFailExitR = -0.1;      // BTC娴泩澶辫触閫€鍑篟
input int    InpBTCNoMFEExitBars = 3;        // BTC鏃犳诞鐩堥€€鍑篵ars
input double InpBTCNoMFEMinPeakR = 0.1;      // BTC鏃犳诞鐩堟渶灏忓嘲鍊?
input double InpBTCNoMFEExitR = -0.25;       // BTC鏃犳诞鐩堥€€鍑篟
input double InpBTCFastSLPeakR = 0.0;        // BTC 快速SL防护峰值R (0=禁用, 设>0启用)
input int    InpBTCFastSLBars  = 2;             // BTC 快速SL检查bars
input double InpBTCFastSLExitR = -0.5;         // BTC 快速SL退出R (负数)
input int    InpBTCLossCutBars = 0;         // BTC 损失定时切损bars (0=禁用, 设>0启用)
input double InpBTCLossCutR = -0.5;         // BTC 损失定时切损R (负数)
input bool   InpBTCEnableHTFNetPushFilter = true; // BTC鍚敤HTF鍑€鎺ㄨ繘
input int    InpBTCHTFNetPushTF = 60;        // BTC HTF鍑€鎺ㄨ繘鍛ㄦ湡
input int    InpBTCHTFNetPushBars = 3;       // BTC HTF鍑€鎺ㄨ繘bars
input double InpBTCHTFNetPushMinATR = 0.35;  // BTC HTF鍑€鎺ㄨ繘闃堝€?
input double InpBTCHTFNetPushAlignedMult = 1.15; // BTC HTF鍚屽悜鍊嶆暟
input double InpBTCHTFNetPushNeutralMult = 1.0;  // BTC HTF涓€у€嶆暟
input double InpBTCHTFNetPushCounterMult = 0.6;  // BTC HTF閫嗗悜鍊嶆暟
input int    InpBTCCloseRetryCooldownSec = 0;    // BTC浜ゆ槗澶辫触鍐峰嵈
input double InpBTCFreeRunMinR = 5.0;       // BTC澶ф诞鐩堜笉璁″苟鍙?
input double InpBTCShallowConfirmPosMin = -0.6; // BTC娴呯‘璁ら槇鍊?
input double InpBTCShallowConfirmPosMult = 0.45; // BTC娴呯‘璁ゅ€嶆暟
input double InpBTCDTPPostPartialLockR = 0.0; // BTC DTP鍒嗘壒鍚庨攣瀹?
input double InpBTCDTPPostPartialRetrace = 0.0; // BTC DTP鍒嗘壒鍚庡洖鎾?
input bool   InpBTCDTPResetPeakAfterPartial = false; // BTC DTP鍒嗘壒鍚庨噸缃嘲鍊?

// 鈹€鈹€ v11 鍗曠瓥鐣?XAU FAGE-alt Profile瑕嗙洊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input bool   InpEnableXAUFageAltProfile = false; // 鍚敤XAU FAGE-alt瑕嗙洊
input string InpXAUFageAltProfileSymbol = "XAU"; // 瑙﹀彂XAU alt profile鐨勫搧绉嶅悕鐗囨
input string InpXAUFageAltProfileMonths = "10"; // 瑙﹀彂XAU alt profile鐨勬湀浠?
input bool   InpXAUFageAltUseMonthFilter = false; // true=鍏佽鏈堜唤瑙﹀彂, false=浠呰嚜閫傚簲瑙﹀彂
input int    InpXAUFageAltAdaptiveStartDay = 5; // 鏈堝唴绗琋澶╁悗鍏佽鑷€傚簲瑙﹀彂
input double InpXAUFageAltAdaptiveMaxBalance = 230.0; // 浣欓浣庝簬璇ュ€艰Е鍙慳lt(0=绂佺敤)
input double InpXAUFageAltAdaptiveMinPrice = 0.0; // 鑷€傚簲瑙﹀彂鏈€灏忎环鏍?0=涓嶉檺)
input double InpXAUFageAltAdaptiveMaxPrice = 0.0; // 鑷€傚簲瑙﹀彂鏈€澶т环鏍?0=涓嶉檺)
input string InpXAUAltContextFilter1Months = "10";
input string InpXAUAltContextFilter1NoHours = "10,11";
input double InpXAUAltContextFilter1Mult = 1.0;
input double InpXAUAltContextFilter2MaxMonthStartBalance = 0.0;
input string InpXAUAltContextFilter2Months = "";
input double InpXAUAltContextFilter2Mult = 1.0;
input string InpXAUAltContextFilter2NoHours = "";
input double InpXAUAltContextFilter3MaxMonthStartBalance = 0.0;
input string InpXAUAltContextFilter3Months = "";
input double InpXAUAltContextFilter3Mult = 1.0;
input string InpXAUAltContextFilter3NoHours = "";
input double InpXAUAltContextFilter4MaxMonthStartBalance = 0.0;
input string InpXAUAltContextFilter4Months = "";
input double InpXAUAltContextFilter4Mult = 1.0;
input string InpXAUAltContextFilter4NoHours = "";
input double InpXAUAltContextFilter5MaxMonthStartBalance = 0.0;
input string InpXAUAltContextFilter5Months = "";
input double InpXAUAltContextFilter5Mult = 1.0;
input string InpXAUAltContextFilter5NoHours = "";
input string InpXAUAltMonthlyProfitTargetStopMonths = "10";

// 鈹€鈹€ 鏈堝垵鐘舵€侀噸缃?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input bool   InpMonthlyZoneReset = false; // 姣忔湀鍒濇竻闄B zone缂撳瓨锛堟秷闄ょ姸鎬佸欢缁奖鍝嶏級
input bool   InpEnableDualZoneChannel = false; // 鍚敤鍙寊one閫氶亾锛圡3鎸崱/M1瓒嬪娍鍚勮嚜鐙珛缁存姢锛屾秷闄ゅ垏鎹㈠共鎵帮級
input int    InpMaxOBAgeBarsTF = 0;  // OB鍔ㄦ€佸勾榫勪笂闄愶紙bars锛?=绂佺敤锛夎秴杩囧垯鑷姩澶辨晥锛屾浛浠ｆ湀鍒濈‖娓呴櫎

// 鈹€鈹€ v11 鍗曠瓥鐣?XAU 瓒嬪娍鐖嗗彂 Profile瑕嗙洊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
input bool   InpEnableXAUTrendProfile = false; // 鍚敤XAU瓒嬪娍鐖嗗彂瑕嗙洊
input string InpXAUTrendProfileSymbol = "XAU"; // 瑙﹀彂XAU瓒嬪娍profile鐨勫搧绉嶅悕鐗囨
input int    InpXAUTrendTriggerTF = 60;        // 瓒嬪娍瑙﹀彂鍑€鎺ㄨ繘鍛ㄦ湡
input int    InpXAUTrendTriggerBars = 3;       // 瓒嬪娍瑙﹀彂鍑€鎺ㄨ繘bars
input double InpXAUTrendMinAbsNetATR = 0.45;   // 瓒嬪娍瑙﹀彂鏈€灏忕粷瀵瑰噣鎺ㄨ繘ATR
input int    InpXAUTrendRangeTF = 240;         // 娉㈠姩鎵╁紶纭鍛ㄦ湡
input int    InpXAUTrendRangeBars = 12;        // 娉㈠姩鎵╁紶纭bars
input double InpXAUTrendMinRangeATR = 4.0;     // 娉㈠姩鎵╁紶鏈€灏忓尯闂碅TR(<=0绂佺敤)
input double InpXAUTrendMinRangeNetATR = 0.0;  // H4鍖洪棿鏂瑰悜鎬у噣鎺ㄨ繘涓嬮檺(0=绂佺敤,寤鸿1.5)
input double InpXAUTrendMinEfficiency = 0.0;   // 瓒嬪娍鍑€鎺ㄨ繘鏁堢巼涓嬮檺=鍑€鎺ㄨ繘/鍖洪棿(0=绂佺敤,寤鸿0.5)
input int    InpTrendConfirmEnterMin = 0;       // 杩涘叆瓒嬪娍妯″紡鎵€闇€鎸佺画婊¤冻鏃堕棿(鍒嗛挓,0=绂佺敤,寤鸿120)
input int    InpTrendConfirmExitMin  = 0;       // 閫€鍑鸿秼鍔挎ā寮忔墍闇€鎸佺画涓嶆弧瓒虫椂闂?鍒嗛挓,0=绂佺敤,寤鸿360)
input int    InpXAUTrendMonthlyLockDays = 0;   // 鏈堝害閿佸畾锛氬墠N澶╄嚜鐢卞垏鎹?N+1澶╄捣璇勪及閿佸畾(0=绂佺敤)
input double InpXAUTrendMonthlyStopLossPct = 0.0; // 瓒嬪娍鑵挎湀鍐呭洖鎾ゅ仠鐢ㄧ櫨鍒嗘瘮(0=绂佺敤)
input string InpXAUTrendContextFilter1Months = "";   // 瓒嬪娍鑵夸笂涓嬫枃杩囨护1鏈堜唤(绌?缁ф壙榛樿)
input string InpXAUTrendContextFilter1NoHours = "";  // 瓒嬪娍鑵夸笂涓嬫枃杩囨护1灞忚斀灏忔椂(绌?缁ф壙榛樿)
input double InpXAUTrendContextFilter1Mult = -1.0;   // 瓒嬪娍鑵夸笂涓嬫枃杩囨护1涔樻暟(<0=缁ф壙榛樿)
input double InpXAUTrendBouncePct = 0.18;
input int    InpXAUTrendTimeoutMin = 120;
input double InpXAUTrendMaxEntryOffsetR = 1.2;
input int    InpXAUTrendBarTF = 1;
input int    InpXAUTrendTimeExitBars = 20;
input double InpXAUTrendBreakevenR = 0.50;
input double InpXAUTrendBreakevenLockR = 0.40;
input double InpXAUTrendDTPTriggerR = 0.0;
input double InpXAUTrendDTPRetrace = 0.20;
input double InpXAUTrendFixedTPR = 1.50;
input double InpXAUTrendRiskPercent = 2.0;
input double InpXAUTrendMaxPosMult = 200.0;
input double InpXAUTrendMaxLotSize = 2.0;
input int    InpXAUTrendMaxConcurrent = 14;
input double InpXAUTrendMinRiskSpreadRatio = 2.5;
input double InpXAUTrendEntryDepthPct = 0.67;
input bool   InpXAUTrendEntryDepthFilter = true;
input bool   InpXAUTrendRequireDoubleTch = false;
input int    InpXAUTrendMaxEntriesPerOB = 20;
input int    InpXAUTrendOBReentryCooldownMin = 0;
input int    InpXAUTrendCooldownBars = 0;
input int    InpXAUTrendFilterContAgeMinBars = 0;
input int    InpXAUTrendFilterContAgeMaxBars = 0;
input bool   InpXAUTrendFilterContNonDeepOnly = false;
input bool   InpXAUTrendEnableHTFNetPushFilter = true;
input int    InpXAUTrendHTFNetPushTF = 60;
input int    InpXAUTrendHTFNetPushBars = 3;
input double InpXAUTrendHTFNetPushMinATR = 0.45;
input double InpXAUTrendHTFNetPushAlignedMult = 1.20;
input double InpXAUTrendHTFNetPushNeutralMult = 0.45;
input double InpXAUTrendHTFNetPushCounterMult = 0.0;

// 鈹€鈹€ v9.8 鍔夸綅鎬佸姩 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
// 鍔?M15瓒嬪娍)
input int    InpTrendLookback     = 80;       // M15瓒嬪娍鍥炴函(bars)
input int    InpSwingStrength     = 3;        // Swing纭寮哄害(宸﹀彸bars)

// 鎬?瓒嬪娍/闇囪崱)
input int    InpSkipStateFilterBars = 0;       // skip state filter first N bars
input bool   InpEnableStateFilter = false;    // 鍚敤鎬佹劅鐭ヨ繃婊?
input double InpRangeBE_R         = 0.0;      // 闇囪崱鎬佷繚鏈琑(0=鐢ㄤ富BE)
input int    InpRangeTimeExit     = 999;      // 闇囪崱鎬佽秴鏃禸ars(999=涓嶈秴鏃?
input double InpTrendBE_R         = 0.0;      // 瓒嬪娍鎬佷繚鏈琑(0=鐢ㄤ富BE)
input double InpTrendBE_Lock      = 0.0;      // 瓒嬪娍鎬佷繚鏈攣瀹歊(0=鐢ㄤ富Lock)
input double InpTrendDTPRetrace   = 0.0;      // 瓒嬪娍鎬丏TP鍥炴挙%(0=鐢ㄤ富Retrace)

// 浣?璇勫垎绯荤粺)
input bool   InpEnableScoring     = false;    // 鍚敤璇勫垎绯荤粺
input int    InpProximityFilter   = 0;        // 0=璇勫垎鍔犳潈, 1=纭繃婊?
input double InpProximityATR      = 1.0;      // 鎺ヨ繎搴﹂槇鍊?ATR鍊嶆暟)
input int    InpMinScore          = 0;        // 鏈€浣庡叆鍦鸿瘎鍒?0=涓嶈繃婊?

// 鍔?鍔ㄨ兘琛板噺)
input bool   InpEnableDecayExit   = false;    // 鍚敤鍔ㄨ兘琛板噺閫€鍑?
input double InpDecayMinR         = 1.0;      // 琛板噺妫€娴嬪惎鍔ㄩ槇鍊?R)
input int    InpDecayBars         = 3;        // 浜屾帹涓嶇牬杩炵画bar鏁?
input int    InpEngulfBodyPct     = 50;       // 鍚炴病杩介殢瀹炰綋鍗犳瘮(%)
input bool   InpEnableMomentumRegime = false; // 鍚敤寮哄急杞崲鎸佷粨绠＄悊
input double InpWeakExitMinR      = 1.0;      // 鍔ㄨ兘杞急閫€鍑烘渶灏廟
input string InpWeakExitFamilyFilter = "";    // 指定信号族使用独立弱退出阈值(如SWP; 空=禁用)
input double InpWeakExitFamilyMinR = 0.0;     // 指定信号族弱退出最小R(0=禁用)
input bool   InpWeakExitRequireReverseContinuation = false; // 弱退出需小周期反向延续确认
input double InpWeakExitHoldLockR = 0.0;      // 弱退出等待反向延续时保护锁R(0=禁用)
input double InpWeakExitLowBalanceThreshold = 0.0; // 低余额弱退出保护阈值(0=禁用)
input double InpWeakExitLowBalanceForceExitR = 0.0; // 低余额弱退出达到该R则直接兑现(0=禁用)
input double InpWeakExitLowBalanceHoldLockR = 0.0; // 低余额弱退出等待时保护锁R(0=禁用)
input double InpWeakBodyShrinkPct = 0.80;     // K1-K3瀹炰綋閫掑噺鍊嶇巼
input double InpWeakWickBodyRatio = 2.0;      // 闀垮奖绾?瀹炰綋闃堝€?
input int    InpStrongMomentumBars = 4;       // 寮哄娍杩炵画K绾挎暟
input double InpStrongMinBodyGrowth = 1.0;    // 寮哄娍鏈牴/棣栨牴瀹炰綋鍊嶇巼
input double InpStrongWeakReverseBodyPct = 25.0; // 寮哄娍涓厑璁哥殑寰急鍙嶅悜瀹炰綋%
input double InpStrongMaxPullbackPct = 35.0;  // 寮哄娍鏈€澶у洖鎾?鎺ㄨ繘%
input double InpStrongDTPRetraceMult = 1.50;  // 寮哄娍鏃禗TP鍥炴挙鏀惧鍊嶆暟
input bool   InpDTPHoldOnContinuation = false; // DTP触发后小周期仍延续则继续持有
input int    InpDTPHoldTF1 = 1;                // DTP持仓检查小周期1(分钟)
input int    InpDTPHoldTF2 = 5;                // DTP持仓检查小周期2(分钟,0=禁用)
input int    InpDTPHoldLookbackBars = 3;       // DTP持仓动能观察bar数
input double InpDTPHoldMinNetATR = 0.20;       // 同向实体净推进/ATR下限
input double InpDTPHoldReverseBodyATR = 0.45;  // 强反向实体/ATR阈值
input double InpDTPHoldBreakBufferATR = 0.05;  // 小结构反转突破缓冲/ATR
input bool   InpDTPHoldRequireHTFAligned = false; // DTP延续持仓需HTF净推进同向
input int    InpDTPHoldMinBounceSec = 0;       // DTP延续持仓的最小确认耗时(0=禁用)
input string InpDTPHoldMinBounceDirections = ""; // DTP延续最小确认耗时作用方向: BUY,SELL; 空=全部方向
input double InpDTPHoldMaxConfirmPos = 999.0;  // DTP延续持仓允许的最浅确认位置
input string InpDTPHoldConfirmPosDirections = ""; // DTP延续确认位置限制方向: BUY,SELL; 空=全部方向
input double InpDTPHoldMinEntryPosMult = 0.0;  // DTP延续持仓要求最小入场仓位倍数(0=禁用)
input string InpDTPHoldMinEntryPosMultDirections = ""; // DTP延续最小入场仓位倍数作用方向: BUY,SELL; 空=全部方向
input bool   InpDTPExitRequireReverseContinuation = false; // DTP出场需反向结构突破+反向延续
input bool   InpDTPExitRequireMomentumWeakness = false; // DTP出场需原方向动能衰弱
input string InpDTPStrictExitFamilies = "";     // 指定信号族才启用严格DTP出场(如BOS,MBOS; 空=全局)
input bool   InpDTPStrictRequireHTFAligned = false; // 严格DTP仅在HTF净推进同向时启用
input int    InpDTPStrictHTFTF = 60;          // 严格DTP对齐检测周期(分钟)
input int    InpDTPStrictHTFBars = 3;         // 严格DTP对齐检测bar数
input double InpDTPStrictHTFMinATR = 0.35;    // 严格DTP同向净推进/ATR下限
input bool   InpConditionalOBTrendRelease = false; // OB入场时小周期延续成立则释放TP/BE截断
input string InpConditionalOBTrendReleaseFamilies = "OB"; // 条件释放适用信号族
input bool   InpConditionalOBTrendReleaseDropTP = true; // 条件释放后清空入场TP
input double InpConditionalOBTrendReleaseBELockR = -1.0; // 条件释放BE锁覆盖(-1=不覆盖)
input double InpConditionalOBTrendReleaseMinEntryPosMult = 0.0; // 条件释放仅作用于入场仓位倍数不低于该值的样本(0=不限)
input string InpConditionalOBTrendReleasePosMultDirections = ""; // 条件释放入场仓位条件作用方向: BUY,SELL; 空=全部方向
input int    InpConditionalOBTrendReleaseTF1 = 1; // 条件释放检查周期1(分钟)
input int    InpConditionalOBTrendReleaseTF2 = 5; // 条件释放检查周期2(分钟,0=禁用)
input int    InpConditionalOBTrendReleaseLookbackBars = 3; // 条件释放动能观察bar数
input double InpConditionalOBTrendReleaseMinNetATR = 0.20; // 同向实体净推进/ATR下限
input double InpConditionalOBTrendReleaseReverseBodyATR = 0.45; // 强反向实体/ATR阈值
input double InpConditionalOBTrendReleaseBreakBufferATR = 0.05; // 小结构反转突破缓冲/ATR
input bool   InpEnableStructureMomentumHold = false; // 结构突破单启用小周期趋势持仓
input string InpStructureHoldFamilies = "";   // 结构持仓适用信号族(如BOS,HTFPB; 空=全局)
input bool   InpStructSkipMFEExits = false;   // 结构持仓跳过MFEFail/NoMFE秒级失败退出
input bool   InpStructMomRequireFullReverseExit = false; // 结构持仓需小周期反转+动能衰弱+反向延续才放弃
input double InpStructMomFullReverseMinR = 0.0; // 启用完整反转退出所需最小浮盈R
input double InpStructProfitLockTriggerR = 0.0; // 结构持仓利润保护触发R(0=禁用)
input double InpStructProfitLockR = 0.0;      // 结构持仓首次锁定R
input double InpStructProfitTrailTriggerR = 0.0; // 结构持仓动态跟随触发R(0=禁用)
input double InpStructProfitTrailLockMult = 0.0; // 结构持仓按峰值R锁定比例
input bool   InpStructProfitLockRequireReverseSignal = false; // 结构利润锁需强反弹/小结构反转
input bool   InpStructureSLRequireHTFAligned = false; // 结构SL仅在HTF净推进同向时启用
input int    InpStructureSLHTFTF = 60;        // 结构SL对齐检测周期(分钟)
input int    InpStructureSLHTFBars = 3;       // 结构SL对齐检测bar数
input double InpStructureSLHTFMinATR = 0.35;  // 结构SL同向净推进/ATR下限
input bool   InpStructureSLRequireStrongBreak = false; // 结构SL需HTF强高低点收盘突破
input int    InpStructureSLStrongBreakTF1 = 60; // 结构SL强突破周期1(分钟)
input int    InpStructureSLStrongBreakTF2 = 240; // 结构SL强突破周期2(分钟,0=禁用)
input int    InpStructureSLStrongBreakLookback = 72; // 查找被突破swing的历史bar数
input int    InpStructureSLStrongBreakMaxAge = 120; // 强突破有效期(对应周期bar数)
input int    InpStructureSLStrongBreakPivot = 2; // 强高低点pivot强度
input double InpStructureSLStrongBreakBufferATR = 0.03; // 收盘突破缓冲(ATR)

// 閮ㄥ垎骞充粨
input double InpPartialCloseR      = 0.0;      // 閮ㄥ垎骞充粨瑙﹀彂R(0=绂佺敤)
input int    InpPartialClosePct    = 50;       // 閮ㄥ垎骞充粨姣斾緥(%)
input double InpPartialPostLockR   = 0.0;      // 閮ㄥ垎骞充粨鍚庡墿浣欎粨閿佸畾R(0=涓嶆彁鎹?
input bool   InpPartialOnlyDeep    = false;    // 浠呮繁浣峅B鍏ュ満鍗曞惎鐢ㄩ儴鍒嗗钩浠?

// 鍏ュ満寮曟搸
input bool   InpEnableEntryEngine  = false;    // 鍚敤鍏ュ満鐘舵€佹満(false=鐩存帴鍏ュ満)

// HTF鐩爣浣?
input bool   InpEnableHTFTarget    = false;    // 澶у皬鍛ㄦ湡鍚屽悜鏃朵娇鐢ㄥぇ鍛ㄦ湡鐩爣浣峊P
input int    InpHTFTargetTF        = 15;       // 澶у懆鏈熺洰鏍囧懆鏈?鍒嗛挓)
input int    InpHTFTargetLookback  = 96;       // 鐩爣浣嶅洖婧痓ars
input int    InpHTFSwingStrength   = 2;        // swing纭寮哄害
input double InpHTFMinTargetR      = 2.0;      // 鐩爣浣嶆渶灏廟
input double InpHTFMaxTargetR      = 6.0;      // 鐩爣浣嶆渶澶(0=涓嶉檺鍒?
input double InpHTFMeasuredMoveR   = 2.0;      // 鏃犳湁鏁堝墠楂樹綆鏃剁殑閲忓害鐩爣R(0=绂佺敤)
input bool   InpHTFRequireAligned  = true;     // 浠呭ぇ灏忓懆鏈熷悓鍚戝惎鐢ㄧ洰鏍?
input double InpHTFPartialR        = 1.0;      // HTF鐩爣鍗曞垎鎵规鐩圧(0=涓嶇敤涓撳睘鍒嗘壒)
input int    InpHTFPartialPct      = 50;       // HTF鐩爣鍗曞垎鎵规瘮渚?
input bool   InpHTFSkipDTP         = false;    // HTF鐩爣鍗曡烦杩囨櫘閫欴TP
input bool   InpHTFSkipTrail       = false;    // HTF鐩爣鍗曡烦杩囨櫘閫歍rail
input double InpHTFDTPTriggerR     = 0.0;      // HTF鐩爣鍗曚笓灞濪TP瑙﹀彂R(0=鐢ㄦ櫘閫欴TP)
input double InpHTFDTPRetrace      = 0.0;      // HTF鐩爣鍗曚笓灞濪TP鍥炴挙(0=鐢ㄦ櫘閫欴TP)
input double InpHTFDTPPostPartialRetrace = 0.0; // HTF鐩爣鍗曞垎鎵瑰悗DTP鍥炴挙(0=娌跨敤)

// 璇婃柇
input bool   InpEnableExitDebug    = false;    // 鎵撳嵃鍑哄満璇婃柇鏃ュ織
input bool   InpEnableEntryDebug   = false;    // 鎵撳嵃鍏ュ満璇婃柇鏃ュ織

input string InpHighBalanceNoEntryMonths = ""; // high month-start balance no-entry months CSV
input double InpHighBalanceNoEntryMinMonthStartBalance = 0.0; // enable when month-start balance >= value

double GetEffectiveEntryDepthPct()
{
   double pct = CfgEntryDepthPct();
   if(InpEntryDepthRelaxMinBalance > 0.0 &&
      pct > 0.0 && pct < 0.67 &&
      AccountInfoDouble(ACCOUNT_BALANCE) < InpEntryDepthRelaxMinBalance)
   {
      pct = 0.67;
   }

   if(pct <= 0.0) return 0.0;
   if(pct >= 1.0) return 1.0;
   return pct;
}

bool UseBTCProfile()
{
   return (InpEnableBTCProfile &&
      StringLen(InpBTCProfileSymbol) > 0 &&
      StringFind(_Symbol, InpBTCProfileSymbol) >= 0);
}

bool CfgCsvIntListed(string csv, int value)
{
   if(StringLen(csv) == 0)
      return false;

   string parts[];
   ushort sep = StringGetCharacter(",", 0);
   int count = StringSplit(csv, sep, parts);
   for(int i = 0; i < count; i++)
   {
      string token = parts[i];
      StringTrimLeft(token);
      StringTrimRight(token);
      if(StringLen(token) == 0)
         continue;
      if((int)StringToInteger(token) == value)
         return true;
   }

   return false;
}


bool CalcXAUTrendStats(int tf_minutes, int bars, double &net_atr, double &range_atr)
{
   bars = MathMax(bars, 1);
   int need = bars + InpATRPeriod + 1;
   MqlRates rates[];
   int count = CopyRates(_Symbol, MinutesToTF(tf_minutes), 1, need, rates);
   if(count < bars + 1)
      return false;

   double atr = CalcATR(rates, count, InpATRPeriod);
   if(atr <= 0)
      return false;

   int start = count - bars;
   double hi = rates[start].high;
   double lo = rates[start].low;
   for(int i = start + 1; i < count; i++)
   {
      hi = MathMax(hi, rates[i].high);
      lo = MathMin(lo, rates[i].low);
   }

   net_atr = (rates[count - 1].close - rates[start].open) / atr;
   range_atr = (hi - lo) / atr;
   return true;
}

bool XAUTrendMonthlyFeedbackAllows()
{
   if(InpXAUTrendMonthlyStopLossPct <= 0)
      return true;

   static int s_key = 0;
   static double s_start_balance = 0.0;
   static bool s_disabled = false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int key = dt.year * 100 + dt.mon;
   if(key != s_key || s_start_balance <= 0)
   {
      s_key = key;
      s_start_balance = AccountInfoDouble(ACCOUNT_BALANCE);
      s_disabled = false;
   }

   if(s_disabled)
      return false;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double stop_balance = s_start_balance * (1.0 - InpXAUTrendMonthlyStopLossPct / 100.0);
   if(balance <= stop_balance)
   {
      s_disabled = true;
      return false;
   }

   return true;
}

bool UseXAUFageAltProfile()
{
   if(!InpEnableXAUFageAltProfile ||
      StringLen(InpXAUFageAltProfileSymbol) <= 0 ||
      StringFind(_Symbol, InpXAUFageAltProfileSymbol) < 0)
      return false;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);

   bool month_trigger = (InpXAUFageAltUseMonthFilter &&
      CfgCsvIntListed(InpXAUFageAltProfileMonths, dt.mon));
   double ref_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ref_price <= 0)
      ref_price = SymbolInfoDouble(_Symbol, SYMBOL_LAST);
   bool price_ok = (ref_price > 0);
   if(price_ok && InpXAUFageAltAdaptiveMinPrice > 0 && ref_price < InpXAUFageAltAdaptiveMinPrice)
      price_ok = false;
   if(price_ok && InpXAUFageAltAdaptiveMaxPrice > 0 && ref_price > InpXAUFageAltAdaptiveMaxPrice)
      price_ok = false;

   bool adaptive_trigger = (InpXAUFageAltAdaptiveStartDay > 0 &&
      InpXAUFageAltAdaptiveMaxBalance > 0 &&
      dt.day >= InpXAUFageAltAdaptiveStartDay &&
      AccountInfoDouble(ACCOUNT_BALANCE) <= InpXAUFageAltAdaptiveMaxBalance &&
      price_ok);

   return (month_trigger || adaptive_trigger);
}

bool CalcXAUTrendProfileRaw()
{
   if(!InpEnableXAUTrendProfile ||
      StringLen(InpXAUTrendProfileSymbol) <= 0 ||
      StringFind(_Symbol, InpXAUTrendProfileSymbol) < 0)
      return false;
   if(!XAUTrendMonthlyFeedbackAllows())
      return false;

   // 鏈堝害閿佸畾锛氬墠N澶╄嚜鐢卞垏鎹紝绗琋+1澶╄捣璇勪及H1鍑€鎺ㄨ繘骞堕攣瀹氬墿浣欐湀浠?
   if(InpXAUTrendMonthlyLockDays > 0)
   {
      static int  s_lock_month    = 0;
      static bool s_lock_decided  = false;
      static bool s_lock_result   = false;

      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);
      int month_key = dt.year * 100 + dt.mon;

      if(month_key != s_lock_month)
      {
         s_lock_month   = month_key;
         s_lock_decided = false;
      }

      if(s_lock_decided) return s_lock_result;

      if(dt.day > InpXAUTrendMonthlyLockDays)
      {
         int   lock_bars = InpXAUTrendMonthlyLockDays * 24;
         double lock_net = 0.0, lock_range = 0.0;
         bool net_ok = CalcXAUTrendStats(InpXAUTrendTriggerTF, lock_bars, lock_net, lock_range)
                       && MathAbs(lock_net) >= InpXAUTrendMinAbsNetATR;

         bool range_ok = true;
         if(InpXAUTrendMinRangeATR > 0)
         {
            double rng_net = 0.0, rng_atr = 0.0;
            range_ok = CalcXAUTrendStats(InpXAUTrendRangeTF, InpXAUTrendRangeBars, rng_net, rng_atr)
                       && rng_atr >= InpXAUTrendMinRangeATR;
            if(range_ok && InpXAUTrendMinRangeNetATR > 0 && MathAbs(rng_net) < InpXAUTrendMinRangeNetATR)
               range_ok = false;
         }

         s_lock_result  = (net_ok && range_ok);
         s_lock_decided = true;
         Print("XAUTrendLock day=", dt.day, " regime=", s_lock_result ? "TREND" : "RANGE",
               " net5d=", lock_net, " net_ok=", net_ok, " range_ok=", range_ok);
         return s_lock_result;
      }
      // 鍓峃澶╋細缁х画瀹炴椂璇勪及锛堣惤鍏ヤ笅鏂规甯搁€昏緫锛?
   }

   double trigger_net = 0.0;
   double trigger_range = 0.0;
   if(!CalcXAUTrendStats(InpXAUTrendTriggerTF, InpXAUTrendTriggerBars, trigger_net, trigger_range))
      return false;
   if(MathAbs(trigger_net) < InpXAUTrendMinAbsNetATR)
      return false;
   if(InpXAUTrendMinEfficiency > 0 && trigger_range > 0 &&
      MathAbs(trigger_net) / trigger_range < InpXAUTrendMinEfficiency)
      return false;

   if(InpXAUTrendMinRangeATR > 0)
   {
      double range_net = 0.0;
      double range_atr = 0.0;
      if(!CalcXAUTrendStats(InpXAUTrendRangeTF, InpXAUTrendRangeBars, range_net, range_atr))
         return false;
      if(range_atr < InpXAUTrendMinRangeATR)
         return false;
      if(InpXAUTrendMinRangeNetATR > 0 && MathAbs(range_net) < InpXAUTrendMinRangeNetATR)
         return false;
   }

   return true;
}

// tick绾х紦瀛?+ 闈炲绉扮‘璁ゆ粸鍚庯細
//   InpTrendConfirmEnterMin: 杩涘叆瓒嬪娍闇€鎸佺画婊¤冻N鍒嗛挓锛堣繃婊ゅ亣瓒嬪娍淇″彿锛?
//   InpTrendConfirmExitMin:  閫€鍑鸿秼鍔块渶鎸佺画涓嶆弧瓒砃鍒嗛挓锛堥槻姝㈢湡瓒嬪娍涓€旈ⅳ鎸級
bool UseXAUTrendProfile()
{
   static datetime s_cache_time     = 0;
   static bool     s_cache_result   = false;

   datetime now = TimeCurrent();
   if(now == s_cache_time) return s_cache_result;

   bool raw = CalcXAUTrendProfileRaw();

   if(InpTrendConfirmEnterMin > 0 || InpTrendConfirmExitMin > 0)
   {
      static bool     s_confirmed     = false;
      static bool     s_last_raw      = false;
      static datetime s_raw_since     = 0;  // 褰撳墠raw鍊兼寔缁紑濮嬬殑鏃堕棿

      if(raw != s_last_raw)
      {
         s_last_raw  = raw;
         s_raw_since = now;
      }

      int confirm_secs = s_confirmed
         ? (InpTrendConfirmExitMin  > 0 ? InpTrendConfirmExitMin  * 60 : 0)   // 閫€鍑虹‘璁ゆ椂闂?
         : (InpTrendConfirmEnterMin > 0 ? InpTrendConfirmEnterMin * 60 : 0);  // 杩涘叆纭鏃堕棿

      // raw 涓庡綋鍓嶇‘璁ょ姸鎬佺浉鍙嶏紙璇存槑鍦ㄥ€掕鏃跺垏鎹腑锛?
      if(raw != s_confirmed && confirm_secs > 0)
      {
         if(now - s_raw_since >= (datetime)confirm_secs)
            s_confirmed = raw;  // 鎸佺画婊¤冻纭鏃堕棿 鈫?鍒囨崲regime
      }
      else if(raw == s_confirmed)
      {
         // raw 涓庣‘璁ょ姸鎬佷竴鑷达細閲嶇疆璁℃椂鍣紙鏃犻渶鍒囨崲锛?
         s_raw_since = now;
      }

      s_cache_result = s_confirmed;
   }
   else
   {
      s_cache_result = raw;
   }

   s_cache_time = now;
   return s_cache_result;
}

double CfgBouncePct() { return UseBTCProfile() ? InpBTCBouncePct : (UseXAUTrendProfile() ? InpXAUTrendBouncePct : InpBouncePct); }
int CfgTimeoutMin() { return UseBTCProfile() ? InpBTCTimeoutMin : (UseXAUTrendProfile() ? InpXAUTrendTimeoutMin : InpTimeoutMin); }
double CfgMaxEntryOffsetR() { return UseBTCProfile() ? InpBTCMaxEntryOffsetR : (UseXAUTrendProfile() ? InpXAUTrendMaxEntryOffsetR : InpMaxEntryOffsetR); }
int CfgBarTF() { return UseBTCProfile() ? InpBTCBarTF : (UseXAUTrendProfile() ? InpXAUTrendBarTF : InpBarTF); }
ENUM_TIMEFRAMES CfgMinutesToTF(int minutes)
{
   switch(minutes)
   {
      case 1:   return PERIOD_M1;
      case 2:   return PERIOD_M2;
      case 3:   return PERIOD_M3;
      case 4:   return PERIOD_M4;
      case 5:   return PERIOD_M5;
      case 6:   return PERIOD_M6;
      case 10:  return PERIOD_M10;
      case 12:  return PERIOD_M12;
      case 15:  return PERIOD_M15;
      case 20:  return PERIOD_M20;
      case 30:  return PERIOD_M30;
      case 60:  return PERIOD_H1;
      case 240: return PERIOD_H4;
      default:  return PERIOD_M15;
   }
}
bool CfgEnableLiquiditySweep() { return UseBTCProfile() ? InpBTCEnableLiquiditySweep : InpEnableLiquiditySweep; }
bool CfgLiquiditySweepOnly() { return UseBTCProfile() ? InpBTCLiquiditySweepOnly : InpLiquiditySweepOnly; }
int CfgNoOBStartHour() { return UseBTCProfile() ? InpBTCNoOBStartHour : InpNoOBStartHour; }
int CfgNoOBEndHour() { return UseBTCProfile() ? InpBTCNoOBEndHour : InpNoOBEndHour; }
double CfgSLBufferATR() { return UseBTCProfile() ? InpBTCSLBufferATR : InpSLBufferATR; }
bool IsDefensiveConfirmActive()
{
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(InpDefensiveConfirmMinPrice > 0 && price < InpDefensiveConfirmMinPrice)
      return false;
   if(InpDefensiveConfirmMaxPrice > 0 && price > InpDefensiveConfirmMaxPrice)
      return false;
   if(InpDefensiveConfirmMaxBalance > 0 &&
      AccountInfoDouble(ACCOUNT_BALANCE) <= InpDefensiveConfirmMaxBalance)
      return true;
   if(IsRuntimeDefensiveModeActive())
      return true;
   return IsMonthlyDefensiveModeActive();
}
int CfgBounceCloseConfirmBars()
{
   if(IsDefensiveConfirmActive() && InpDefensiveBounceCloseConfirmBars > 0)
      return InpDefensiveBounceCloseConfirmBars;
   return InpBounceCloseConfirmBars;
}
double CfgBounceCloseBufferPct()
{
   if(IsDefensiveConfirmActive() && InpDefensiveBounceCloseConfirmBars > 0)
      return InpDefensiveBounceCloseBufferPct;
   return InpBounceCloseBufferPct;
}
bool CfgBounceCloseRequireBody()
{
   if(IsDefensiveConfirmActive() && InpDefensiveBounceCloseConfirmBars > 0)
      return InpDefensiveBounceCloseRequireBody;
   return InpBounceCloseRequireBody;
}
double CfgBounceCloseMinBodyPct()
{
   if(IsDefensiveConfirmActive() && InpDefensiveBounceCloseConfirmBars > 0)
      return InpDefensiveBounceCloseMinBodyPct;
   return InpBounceCloseMinBodyPct;
}
double CfgBounceCloseWeakBodyPct()
{
   if(IsDefensiveConfirmActive() && InpDefensiveBounceCloseConfirmBars > 0)
      return InpDefensiveBounceCloseWeakBodyPct;
   return InpBounceCloseWeakBodyPct;
}
double CfgBounceCloseWeakBodyMult()
{
   if(IsDefensiveConfirmActive() && InpDefensiveBounceCloseConfirmBars > 0)
      return InpDefensiveBounceCloseWeakBodyMult;
   return InpBounceCloseWeakBodyMult;
}
int CfgVirtualSLConfirmBars()
{
   if(IsDefensiveConfirmActive() && InpDefensiveVirtualSLConfirmBars > 0)
      return InpDefensiveVirtualSLConfirmBars;
   return InpVirtualSLConfirmBars;
}
int CfgVirtualSLConfirmTF() { return InpVirtualSLConfirmTF; }
double CfgVirtualSLHardBufferR()
{
   if(IsDefensiveConfirmActive() && InpDefensiveVirtualSLConfirmBars > 0)
      return InpDefensiveVirtualSLHardBufferR;
   return InpVirtualSLHardBufferR;
}
double CfgVirtualSLCloseBufferATR()
{
   if(IsDefensiveConfirmActive() && InpDefensiveVirtualSLConfirmBars > 0)
      return InpDefensiveVirtualSLCloseBufferATR;
   return InpVirtualSLCloseBufferATR;
}
double CfgOBHeightTPMult() { return UseBTCProfile() ? InpBTCOBHeightTPMult : InpOBHeightTPMult; }
int CfgVirtualSLBreachSec() { return InpVirtualSLBreachSec; }
int CfgTimeExitBars() { return UseBTCProfile() ? InpBTCTimeExitBars : (UseXAUTrendProfile() ? InpXAUTrendTimeExitBars : InpTimeExitBars); }
int CfgSweepLookbackBars() { return UseBTCProfile() ? InpBTCSweepLookbackBars : InpSweepLookbackBars; }
double CfgSweepMaxRangeATR() { return UseBTCProfile() ? InpBTCSweepMaxRangeATR : InpSweepMaxRangeATR; }
double CfgSweepMinRangeSpreadMult() { return UseBTCProfile() ? InpBTCSweepMinRangeSpreadMult : InpSweepMinRangeSpreadMult; }
double CfgSweepMinPenetrationATR() { return UseBTCProfile() ? InpBTCSweepMinPenetrationATR : InpSweepMinPenetrationATR; }
double CfgSweepMinWickPct() { return UseBTCProfile() ? InpBTCSweepMinWickPct : InpSweepMinWickPct; }
double CfgSweepTPMult() { return UseBTCProfile() ? InpBTCSweepTPMult : InpSweepTPMult; }
double CfgBreakevenR() { return UseBTCProfile() ? InpBTCBreakevenR : (UseXAUTrendProfile() ? InpXAUTrendBreakevenR : InpBreakevenR); }
double CfgBreakevenLockR() { return UseBTCProfile() ? InpBTCBreakevenLockR : (UseXAUTrendProfile() ? InpXAUTrendBreakevenLockR : InpBreakevenLockR); }
double CfgBreakevenStage2R() { return InpBreakevenStage2R; }
double CfgBreakevenStage2LockR() { return InpBreakevenStage2LockR; }
double CfgDTPTriggerR() { return UseBTCProfile() ? InpBTCDTPTriggerR : (UseXAUTrendProfile() ? InpXAUTrendDTPTriggerR : InpDTPTriggerR); }
double CfgDTPRetrace() { return UseBTCProfile() ? InpBTCDTPRetrace : (UseXAUTrendProfile() ? InpXAUTrendDTPRetrace : InpDTPRetrace); }
double CfgFixedTPR() { return UseBTCProfile() ? InpBTCFixedTPR : (UseXAUTrendProfile() ? InpXAUTrendFixedTPR : InpFixedTPR); }
double CfgEffectiveFixedTPR() {
    double base = CfgFixedTPR();
    if(UseVirtualSLMode() && CfgVirtualSLHardBufferR() > 0.0)
        return base + CfgVirtualSLHardBufferR();
    return base;
}
double CfgRiskPercent() { return UseBTCProfile() ? InpBTCRiskPercent : (UseXAUTrendProfile() ? InpXAUTrendRiskPercent : InpRiskPercent); }
double CfgMaxPosMult() { return UseBTCProfile() ? InpBTCMaxPosMult : (UseXAUTrendProfile() ? InpXAUTrendMaxPosMult : InpMaxPosMult); }
double CfgMaxLotSize() { return UseBTCProfile() ? InpBTCMaxLotSize : (UseXAUTrendProfile() ? InpXAUTrendMaxLotSize : InpMaxLotSize); }
int CfgMaxConcurrent() { return UseBTCProfile() ? InpBTCMaxConcurrent : (UseXAUTrendProfile() ? InpXAUTrendMaxConcurrent : InpMaxConcurrent); }
double CfgMinRiskSpreadRatio() { return UseBTCProfile() ? InpBTCMinRiskSpreadRatio : (UseXAUTrendProfile() ? InpXAUTrendMinRiskSpreadRatio : InpMinRiskSpreadRatio); }
double CfgSweepPosMult() { return UseBTCProfile() ? InpBTCSweepPosMult : InpSweepPosMult; }
double CfgSweepMaxLotSize() { return UseBTCProfile() ? InpBTCSweepMaxLotSize : InpSweepMaxLotSize; }
double CfgLowBalanceThreshold() { return UseBTCProfile() ? InpBTCLowBalanceThreshold : InpLowBalanceThreshold; }
double CfgLowBalancePosMult() { return UseBTCProfile() ? InpBTCLowBalancePosMult : InpLowBalancePosMult; }
double CfgLowBalanceMaxLotSize() { return UseBTCProfile() ? InpBTCLowBalanceMaxLotSize : InpLowBalanceMaxLotSize; }
double CfgEntryDepthPct() { return UseBTCProfile() ? InpBTCEntryDepthPct : (UseXAUTrendProfile() ? InpXAUTrendEntryDepthPct : InpEntryDepthPct); }
bool CfgEntryDepthFilter() { return UseBTCProfile() ? InpBTCEntryDepthFilter : (UseXAUTrendProfile() ? InpXAUTrendEntryDepthFilter : InpEntryDepthFilter); }
bool CfgRequireDoubleTch() { return UseBTCProfile() ? InpBTCRequireDoubleTch : (UseXAUTrendProfile() ? InpXAUTrendRequireDoubleTch : InpRequireDoubleTch); }
int CfgMaxEntriesPerOB()
{
   if(!UseBTCProfile() && IsDefensiveConfirmActive() && InpDefensiveMaxEntriesPerOB > 0)
      return InpDefensiveMaxEntriesPerOB;
   return UseBTCProfile() ? InpBTCMaxEntriesPerOB : (UseXAUTrendProfile() ? InpXAUTrendMaxEntriesPerOB : InpMaxEntriesPerOB);
}
int CfgOBReentryCooldownMin()
{
   // 自适应噪音门控防守态: 打断OB震荡重入连亏链(2603发现17连亏)
   if(!UseBTCProfile() && IsAdaptiveNoiseGateDefensive() && InpAdaptiveNoiseDefOBReentryCd > 0)
      return InpAdaptiveNoiseDefOBReentryCd;
   if(!UseBTCProfile() && IsDefensiveConfirmActive() && InpDefensiveOBReentryCooldownMin > 0)
      return InpDefensiveOBReentryCooldownMin;
   return UseBTCProfile() ? InpBTCOBReentryCooldownMin : (UseXAUTrendProfile() ? InpXAUTrendOBReentryCooldownMin : InpOBReentryCooldownMin);
}
int CfgCooldownBars() { return UseBTCProfile() ? InpBTCCooldownBars : (UseXAUTrendProfile() ? InpXAUTrendCooldownBars : InpCooldownBars); }
double CfgContinuationPosMult() { return UseBTCProfile() ? InpBTCContinuationPosMult : InpContinuationPosMult; }
int CfgFilterContAgeMinBars() { return UseBTCProfile() ? InpBTCFilterContAgeMinBars : (UseXAUTrendProfile() ? InpXAUTrendFilterContAgeMinBars : InpFilterContAgeMinBars); }
int CfgFilterContAgeMaxBars() { return UseBTCProfile() ? InpBTCFilterContAgeMaxBars : (UseXAUTrendProfile() ? InpXAUTrendFilterContAgeMaxBars : InpFilterContAgeMaxBars); }
bool CfgFilterContNonDeepOnly() { return UseBTCProfile() ? InpBTCFilterContNonDeepOnly : (UseXAUTrendProfile() ? InpXAUTrendFilterContNonDeepOnly : InpFilterContNonDeepOnly); }
double CfgBoostIn1HOB() { return UseBTCProfile() ? InpBTCBoostIn1HOB : InpBoostIn1HOB; }
// CfgAdaptiveBoostIn1HOB/CfgAdaptiveDeepEntryBoost/CfgAdaptiveMaxPosMult 实现在SignalEngine.mqh
int CfgLateBounceSec() { return UseBTCProfile() ? InpBTCLateBounceSec : InpLateBounceSec; }
double CfgLateBounceMult() { return UseBTCProfile() ? InpBTCLateBounceMult : InpLateBounceMult; }
double CfgBounceSweetMinPct() { return UseBTCProfile() ? InpBTCBounceSweetMinPct : InpBounceSweetMinPct; }
double CfgBounceSweetMaxPct() { return UseBTCProfile() ? InpBTCBounceSweetMaxPct : InpBounceSweetMaxPct; }
double CfgOutsideBounceSweetMult() { return UseBTCProfile() ? InpBTCOutsideBounceSweetMult : InpOutsideBounceSweetMult; }
double CfgDefensiveBounceSweetMinPct()
{
   if(!UseBTCProfile() && IsDefensiveConfirmActive() && InpDefensiveBounceSweetMinPct > 0)
      return InpDefensiveBounceSweetMinPct;
   return CfgBounceSweetMinPct();
}
double CfgDefensiveBounceSweetMaxPct()
{
   if(!UseBTCProfile() && IsDefensiveConfirmActive() && InpDefensiveBounceSweetMinPct > 0)
      return InpDefensiveBounceSweetMaxPct;
   return CfgBounceSweetMaxPct();
}
double CfgDefensiveOutsideBounceSweetMult()
{
   if(!UseBTCProfile() && IsDefensiveConfirmActive() && InpDefensiveBounceSweetMinPct > 0)
      return InpDefensiveOutsideBounceSweetMult;
   return CfgOutsideBounceSweetMult();
}
double CfgBadRiskMin() { return UseBTCProfile() ? InpBTCBadRiskMin : InpBadRiskMin; }
double CfgBadRiskMax() { return UseBTCProfile() ? InpBTCBadRiskMax : InpBadRiskMax; }
double CfgBadRiskMult() { return UseBTCProfile() ? InpBTCBadRiskMult : InpBadRiskMult; }
double CfgLargeRiskMin() { return UseBTCProfile() ? InpBTCLargeRiskMin : InpLargeRiskMin; }
double CfgLargeRiskMult() { return UseBTCProfile() ? InpBTCLargeRiskMult : InpLargeRiskMult; }
double CfgDeepFastConfirmPosMax() { return InpDeepFastConfirmPosMax; }
int CfgDeepFastConfirmSecMax() { return InpDeepFastConfirmSecMax; }
double CfgDeepFastConfirmMult() { return InpDeepFastConfirmMult; }
double CfgDeepFastConfirmBounceMinPct() { return InpDeepFastConfirmBounceMinPct; }
double CfgDeepFastConfirmBounceMaxPct() { return InpDeepFastConfirmBounceMaxPct; }
string CfgNoEntryHours() { return UseBTCProfile() ? InpBTCNoEntryHours : InpNoEntryHours; }
string CfgNoBuyHours() { return UseBTCProfile() ? InpBTCNoBuyHours : InpNoBuyHours; }
string CfgNoSellHours() { return UseBTCProfile() ? InpBTCNoSellHours : InpNoSellHours; }
string CfgLowRiskHours() { return UseBTCProfile() ? InpBTCLowRiskHours : InpLowRiskHours; }
double CfgLowRiskHourMult() { return UseBTCProfile() ? InpBTCLowRiskHourMult : InpLowRiskHourMult; }
string CfgHighRiskHours() { return UseBTCProfile() ? InpBTCHighRiskHours : InpHighRiskHours; }
double CfgHighRiskHourMult() { return UseBTCProfile() ? InpBTCHighRiskHourMult : InpHighRiskHourMult; }
bool CfgEnableStateFilter() { return UseBTCProfile() ? InpBTCEnableStateFilter : InpEnableStateFilter; }
int CfgTrendLookback() { return UseBTCProfile() ? InpBTCTrendLookback : InpTrendLookback; }
int CfgSwingStrength() { return UseBTCProfile() ? InpBTCSwingStrength : InpSwingStrength; }
double CfgRangeBE_R() { return UseBTCProfile() ? InpBTCRangeBE_R : InpRangeBE_R; }
int CfgRangeTimeExit() { return UseBTCProfile() ? InpBTCRangeTimeExit : InpRangeTimeExit; }
double CfgTrendBE_R() { return UseBTCProfile() ? InpBTCTrendBE_R : InpTrendBE_R; }
double CfgTrendBE_Lock() { return UseBTCProfile() ? InpBTCTrendBE_Lock : InpTrendBE_Lock; }
double CfgTrendDTPRetrace() { return UseBTCProfile() ? InpBTCTrendDTPRetrace : InpTrendDTPRetrace; }
bool CfgEnableScoring() { return UseBTCProfile() ? InpBTCEnableScoring : InpEnableScoring; }
int CfgMinScore() { return UseBTCProfile() ? InpBTCMinScore : InpMinScore; }
double CfgProximityATR() { return UseBTCProfile() ? InpBTCProximityATR : InpProximityATR; }
bool CfgEnableDecayExit() { return UseBTCProfile() ? InpBTCEnableDecayExit : InpEnableDecayExit; }
double CfgDecayMinR() { return UseBTCProfile() ? InpBTCDecayMinR : InpDecayMinR; }
int CfgDecayBars() { return UseBTCProfile() ? InpBTCDecayBars : InpDecayBars; }
double CfgMFEFailMinR() { return UseBTCProfile() ? InpBTCMFEFailMinR : InpMFEFailMinR; }
double CfgMFEFailExitR() { return UseBTCProfile() ? InpBTCMFEFailExitR : InpMFEFailExitR; }
int CfgNoMFEExitBars() { return UseBTCProfile() ? InpBTCNoMFEExitBars : InpNoMFEExitBars; }
double CfgNoMFEMinPeakR() { return UseBTCProfile() ? InpBTCNoMFEMinPeakR : InpNoMFEMinPeakR; }
double CfgNoMFEExitR() { return UseBTCProfile() ? InpBTCNoMFEExitR : InpNoMFEExitR; }
bool CfgEnableHTFNetPushFilter() { return UseBTCProfile() ? InpBTCEnableHTFNetPushFilter : (UseXAUTrendProfile() ? InpXAUTrendEnableHTFNetPushFilter : InpEnableHTFNetPushFilter); }
int CfgHTFNetPushTF() { return UseBTCProfile() ? InpBTCHTFNetPushTF : (UseXAUTrendProfile() ? InpXAUTrendHTFNetPushTF : InpHTFNetPushTF); }
int CfgHTFNetPushBars() { return UseBTCProfile() ? InpBTCHTFNetPushBars : (UseXAUTrendProfile() ? InpXAUTrendHTFNetPushBars : InpHTFNetPushBars); }
double CfgHTFNetPushMinATR() { return UseBTCProfile() ? InpBTCHTFNetPushMinATR : (UseXAUTrendProfile() ? InpXAUTrendHTFNetPushMinATR : InpHTFNetPushMinATR); }
double CfgHTFNetPushAlignedMult() { return UseBTCProfile() ? InpBTCHTFNetPushAlignedMult : (UseXAUTrendProfile() ? InpXAUTrendHTFNetPushAlignedMult : InpHTFNetPushAlignedMult); }
double CfgHTFNetPushNeutralMult() { return UseBTCProfile() ? InpBTCHTFNetPushNeutralMult : (UseXAUTrendProfile() ? InpXAUTrendHTFNetPushNeutralMult : InpHTFNetPushNeutralMult); }
double CfgHTFNetPushCounterMult() { return UseBTCProfile() ? InpBTCHTFNetPushCounterMult : (UseXAUTrendProfile() ? InpXAUTrendHTFNetPushCounterMult : InpHTFNetPushCounterMult); }
int CfgCloseRetryCooldownSec() { return UseBTCProfile() ? InpBTCCloseRetryCooldownSec : InpCloseRetryCooldownSec; }
double CfgFreeRunMinR() { return UseBTCProfile() ? InpBTCFreeRunMinR : InpFreeRunMinR; }
double CfgShallowConfirmPosMin()
{
   if(!UseBTCProfile() && IsDefensiveConfirmActive() && InpDefensiveShallowConfirmPosMin > -999.0)
      return InpDefensiveShallowConfirmPosMin;
   return UseBTCProfile() ? InpBTCShallowConfirmPosMin : InpShallowConfirmPosMin;
}
double CfgShallowConfirmPosMult()
{
   if(!UseBTCProfile() && IsDefensiveConfirmActive() && InpDefensiveShallowConfirmPosMin > -999.0)
      return InpDefensiveShallowConfirmPosMult;
   return UseBTCProfile() ? InpBTCShallowConfirmPosMult : InpShallowConfirmPosMult;
}
double CfgDTPPostPartialLockR() { return UseBTCProfile() ? InpBTCDTPPostPartialLockR : InpDTPPostPartialLockR; }
double CfgDTPPostPartialRetrace() { return UseBTCProfile() ? InpBTCDTPPostPartialRetrace : InpDTPPostPartialRetrace; }
bool CfgDTPResetPeakAfterPartial() { return UseBTCProfile() ? InpBTCDTPResetPeakAfterPartial : InpDTPResetPeakAfterPartial; }
// --- Mitigation Entry accessors ---
bool CfgEnableMitigationEntry() { return InpEnableMitigationEntry; }
int  CfgMitigationEntryMaxBars() { return InpMitigationEntryMaxBars; }
bool CfgMitigationEntryOnlyRange() { return InpMitigationEntryOnlyRange; }
bool CfgMitigationEntryOnlyDefensive() { return InpMitigationEntryOnlyDefensive; }
string CfgMitigationEntrySignalTypes() { return InpMitigationEntrySignalTypes; }
// --- 双扫确认 accessors ---
bool CfgEnableDoubleSweepConfirm() { return InpEnableDoubleSweepConfirm; }
int  CfgDoubleSweepWindowBars() { return InpDoubleSweepWindowBars; }
bool CfgDoubleSweepOnlyDefensive() { return InpDoubleSweepOnlyDefensive; }
bool CfgDoubleSweepBlockSweepEntry() { return InpDoubleSweepBlockSweepEntry; }
double CfgDoubleSweepDTPTriggerR() { return InpDoubleSweepDTPTriggerR; }
double CfgDoubleSweepRegimePosMult() { return InpDoubleSweepRegimePosMult; }
// --- FVG accessors ---
bool   CfgEnableFVG()              { return InpEnableFVG; }
int    CfgFVGLookbackBars()        { return InpFVGLookbackBars; }
double CfgFVGMinGapATR()           { return InpFVGMinGapATR; }
double CfgFVGMaxGapATR()           { return InpFVGMaxGapATR; }
int    CfgFVGMaxAgeBars()          { return InpFVGMaxAgeBars; }
int    CfgFVGTimeoutMin()          { return InpFVGTimeoutMin; }
bool   CfgFVGRequireRangeBoundary(){ return InpFVGRequireRangeBoundary; }
bool   CfgFVGEnableFadeEntry()     { return InpFVGEnableFadeEntry; }
double CfgFVGFadeMinRiskSpreadRatio() { return InpFVGFadeMinRiskSpreadRatio; }
double CfgFVGFadeMaxEntryOffsetR() { return InpFVGFadeMaxEntryOffsetR; }
double CfgFVGFadePosMult()         { return InpFVGFadePosMult; }
double CfgFVGFadeMaxLotSize()      { return InpFVGFadeMaxLotSize; }
double CfgFVGFadeTPMult()          { return InpFVGFadeTPMult; }
string CfgFVGNoEntryHours()        { return InpFVGNoEntryHours; }
bool   CfgFVGRequireConfirmCandle(){ return InpFVGRequireConfirmCandle; }
bool   CfgFVGRequireH1Aligned()    { return InpFVGRequireH1Aligned; }
bool   CfgEnableHTFDirectionGate() { return InpEnableHTFDirectionGate; }
// --- HTF Range Fade accessors ---
bool   CfgEnableRangeFade()             { return InpEnableRangeFade; }
int    CfgRangeTF()                     { return InpRangeTF; }
int    CfgRangeLookback()               { return InpRangeLookback; }
int    CfgRangeMinBars()                { return InpRangeMinBars; }
double CfgRangeMinWidthATR()            { return InpRangeMinWidthATR; }
double CfgRangeMaxWidthATR()            { return InpRangeMaxWidthATR; }
double CfgRangeBoundaryToleranceATR()   { return InpRangeBoundaryToleranceATR; }
int    CfgRangeSwingStrength()          { return InpRangeSwingStrength; }
int    CfgRangeMinTouches()             { return InpRangeMinTouches; }
double CfgRangeMinContainment()         { return InpRangeMinContainment; }
double CfgRangeEntryZoneATR()           { return InpRangeEntryZoneATR; }
double CfgRangeSLBufferATR()            { return InpRangeSLBufferATR; }
int    CfgRangeTPTarget()              { return InpRangeTPTarget; }
double CfgRangePosMult()               { return InpRangePosMult; }
double CfgRangeMaxLot()                { return InpRangeMaxLot; }
int    CfgRangeUpdateBars()             { return InpRangeUpdateBars; }
bool   CfgRangeRequireSweep()           { return InpRangeRequireSweep; }
bool   CfgRangeRequireFVG()             { return InpRangeRequireFVG; }
bool   CfgRangeNoMidTrades()            { return InpRangeNoMidTrades; }
bool   CfgRangeApplyAlignedSignal()     { return CfgRangeTPTarget() == 3; }
bool   CfgRangeConfirmSignalOnly()      { return CfgRangeTPTarget() == 4; }
bool   CfgRangeDirectionGateOnly()      { return CfgRangeTPTarget() == 5; }
bool   CfgRangeDTPStrictQualityOnly()   { return CfgRangeTPTarget() == 6; }
bool   CfgRangeHTFOBReactionOnly()      { return CfgRangeTPTarget() == 7; }
bool   CfgRangeHTFRejectContextOnly()   { return CfgRangeTPTarget() == 8; }
bool   CfgRangeHTFRejectContextEnabled(){ return CfgRangeHTFOBReactionOnly() || CfgRangeHTFRejectContextOnly(); }
bool   CfgRangeContextDetectorEnabled() { return CfgEnableRangeFade() || CfgRangeHTFRejectContextOnly(); }
string CfgContextFilter1Months()  {
   if(UseXAUTrendProfile() && StringLen(InpXAUTrendContextFilter1Months) > 0)  return InpXAUTrendContextFilter1Months;
   return UseXAUFageAltProfile() ? InpXAUAltContextFilter1Months : InpContextFilter1Months;
}
string CfgContextFilter1NoHours() {
   if(UseXAUTrendProfile() && StringLen(InpXAUTrendContextFilter1NoHours) > 0) return InpXAUTrendContextFilter1NoHours;
   return UseXAUFageAltProfile() ? InpXAUAltContextFilter1NoHours : InpContextFilter1NoHours;
}
string CfgContextFilter1NoBuyHours() { return InpContextFilter1NoBuyHours; }
string CfgContextFilter1NoSellHours() { return InpContextFilter1NoSellHours; }
double CfgContextFilter1MinMonthStartBalance() { return InpContextFilter1MinMonthStartBalance; }
double CfgContextFilter1MaxMonthStartBalance() { return InpContextFilter1MaxMonthStartBalance; }
double CfgContextFilter1MaxBalance() { return InpContextFilter1MaxBalance; }
double CfgContextFilter1MinPrice() { return InpContextFilter1MinPrice; }
double CfgContextFilter1MaxPrice() { return InpContextFilter1MaxPrice; }
double CfgContextFilter1Mult() {
   if(UseXAUTrendProfile() && InpXAUTrendContextFilter1Mult >= 0) return InpXAUTrendContextFilter1Mult;
   return UseXAUFageAltProfile() ? InpXAUAltContextFilter1Mult : InpContextFilter1Mult;
}
string CfgContextFilter2Months() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter2Months : InpContextFilter2Months; }
string CfgContextFilter2NoHours() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter2NoHours : InpContextFilter2NoHours; }
string CfgContextFilter2NoBuyHours() { return InpContextFilter2NoBuyHours; }
string CfgContextFilter2NoSellHours() { return InpContextFilter2NoSellHours; }
double CfgContextFilter2MinMonthStartBalance() { return InpContextFilter2MinMonthStartBalance; }
double CfgContextFilter2MaxMonthStartBalance() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter2MaxMonthStartBalance : InpContextFilter2MaxMonthStartBalance; }
double CfgContextFilter2MaxBalance() { return InpContextFilter2MaxBalance; }
double CfgContextFilter2MinPrice() { return InpContextFilter2MinPrice; }
double CfgContextFilter2MaxPrice() { return InpContextFilter2MaxPrice; }
double CfgContextFilter2Mult() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter2Mult : InpContextFilter2Mult; }
string CfgContextFilter3Months() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter3Months : InpContextFilter3Months; }
string CfgContextFilter3NoHours() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter3NoHours : InpContextFilter3NoHours; }
string CfgContextFilter3NoBuyHours() { return InpContextFilter3NoBuyHours; }
string CfgContextFilter3NoSellHours() { return InpContextFilter3NoSellHours; }
double CfgContextFilter3MinMonthStartBalance() { return InpContextFilter3MinMonthStartBalance; }
double CfgContextFilter3MaxMonthStartBalance() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter3MaxMonthStartBalance : InpContextFilter3MaxMonthStartBalance; }
double CfgContextFilter3MaxBalance() { return InpContextFilter3MaxBalance; }
double CfgContextFilter3MinPrice() { return InpContextFilter3MinPrice; }
double CfgContextFilter3MaxPrice() { return InpContextFilter3MaxPrice; }
double CfgContextFilter3Mult() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter3Mult : InpContextFilter3Mult; }
string CfgContextFilter4Months() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter4Months : InpContextFilter4Months; }
string CfgContextFilter4NoHours() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter4NoHours : InpContextFilter4NoHours; }
string CfgContextFilter4NoBuyHours() { return InpContextFilter4NoBuyHours; }
string CfgContextFilter4NoSellHours() { return InpContextFilter4NoSellHours; }
double CfgContextFilter4MinMonthStartBalance() { return InpContextFilter4MinMonthStartBalance; }
double CfgContextFilter4MaxMonthStartBalance() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter4MaxMonthStartBalance : InpContextFilter4MaxMonthStartBalance; }
double CfgContextFilter4MaxBalance() { return InpContextFilter4MaxBalance; }
double CfgContextFilter4MinPrice() { return InpContextFilter4MinPrice; }
double CfgContextFilter4MaxPrice() { return InpContextFilter4MaxPrice; }
double CfgContextFilter4Mult() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter4Mult : InpContextFilter4Mult; }
string CfgContextFilter5Months() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter5Months : InpContextFilter5Months; }
string CfgContextFilter5NoHours() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter5NoHours : InpContextFilter5NoHours; }
string CfgContextFilter5NoBuyHours() { return InpContextFilter5NoBuyHours; }
string CfgContextFilter5NoSellHours() { return InpContextFilter5NoSellHours; }
double CfgContextFilter5MinMonthStartBalance() { return InpContextFilter5MinMonthStartBalance; }
double CfgContextFilter5MaxMonthStartBalance() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter5MaxMonthStartBalance : InpContextFilter5MaxMonthStartBalance; }
double CfgContextFilter5MaxBalance() { return InpContextFilter5MaxBalance; }
double CfgContextFilter5MinPrice() { return InpContextFilter5MinPrice; }
double CfgContextFilter5MaxPrice() { return InpContextFilter5MaxPrice; }
double CfgContextFilter5Mult() { return UseXAUFageAltProfile() ? InpXAUAltContextFilter5Mult : InpContextFilter5Mult; }
string CfgMonthlyProfitTargetStopMonths() { return UseXAUFageAltProfile() ? InpXAUAltMonthlyProfitTargetStopMonths : InpMonthlyProfitTargetStopMonths; }

#endif