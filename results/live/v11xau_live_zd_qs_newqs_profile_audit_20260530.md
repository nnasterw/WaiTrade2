# MT5 portfolio profile audit

profile=temp\portfolio_profiles\v11xau_live_zd_qs_newqs\v11xau_live_zd_qs
schedule=v11xau_live_zd_qs

| chart | stream | version | magic | shared_key | sweep_months | sweep_no_hours | context_filters | pass |
|---|---|---|---:|---|---|---|---|---|
| chart01.chr | ZD | V11XAU-ZD-ZD | 204800 |  |  |  | s3:m=- mult=0.0 h=7,11,13 max=500.0<br>s4:m=- mult=5.0 h=14 max=500.0 | true |
| chart02.chr | QS | V11XAU-QS-HIGHPRICE-LOWBAL-OBVSL-BODY45-REENTRY3-POS100-250-QS | 205005 |  |  |  | s1:m=- mult=1.0 buy=7 sell=3,8 max=1000.0 | true |

charts=2 versions=2 unique_magics=2 pass=true
