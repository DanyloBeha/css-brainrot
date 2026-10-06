# Numbers behind the notebook text

Written by `python -m src.checks` (numeric tables only; row-level text is never saved).

### raw profile

```
          kind          subreddit     rows      ids               first                last  deleted_author  bot_suffix  removed_text
0     comments              books  1876751  1876751 2012-01-02 00:00:33 2026-09-30 23:58:38        152967.0      1809.0      108789.0
1     comments  explainlikeimfive  1852536  1852536 2012-01-01 12:00:37 2026-09-30 23:59:07        240078.0      2981.0      204669.0
2     comments              memes  1334537  1334537 2012-01-01 16:29:04 2026-09-29 20:59:55        123774.0      7699.0      109822.0
3     comments             nosurf   478540   478540 2012-01-02 10:07:16 2026-09-30 23:45:52         49665.0      1402.0       28472.0
4     comments          teenagers  1843775  1843775 2012-01-06 00:01:42 2026-09-30 10:29:56        192508.0      4888.0      100737.0
5     comments      todayilearned  1851066  1851066 2012-01-01 08:00:19 2026-09-29 17:59:54        159766.0      3041.0      116006.0
0  submissions              books   368255   368255 2012-01-01 00:38:06 2026-09-28 23:44:10         61939.0       113.0      168211.0
1  submissions  explainlikeimfive   369085   369085 2012-01-01 00:09:41 2026-09-30 23:58:34         83616.0       224.0      173760.0
2  submissions              memes   343402   343402 2012-01-01 02:25:27 2026-09-30 23:53:05         78358.0       154.0       65167.0
3  submissions             nosurf    56057    56057 2012-01-02 10:05:48 2026-09-30 22:30:45         11107.0        21.0       11238.0
4  submissions          teenagers   363975   363975 2012-01-01 00:05:41 2026-09-27 23:57:35        100414.0       423.0       81336.0
5  submissions      todayilearned   369483   369483 2012-01-01 00:02:20 2026-09-30 23:55:46         91487.0       203.0       61307.0
```

### r/nosurf spike days (typical day = median since 2020 in the last row)

```
                        d  comments  threads   top1  top1_share  top3_share
3963  2020-04-15 00:00:00     238.0     49.0   59.0        0.25        0.52
2535  2021-02-12 00:00:00     243.0     37.0   41.0        0.17        0.41
2768  2021-12-30 00:00:00     270.0     38.0   89.0        0.33        0.63
345   2024-01-25 00:00:00     351.0     43.0  112.0        0.32        0.55
2378  2024-03-22 00:00:00     367.0     43.0  122.0        0.33        0.53
1932  2024-08-16 00:00:00     342.0     49.0   93.0        0.27        0.55
2278  2024-12-19 00:00:00     382.0     51.0  106.0        0.28        0.46
273   2025-09-11 00:00:00     530.0     58.0  160.0        0.30        0.72
0                 typical     131.0     33.0    NaN        0.21        0.43
```

### crisis words per 10,000: 3-month peak and monthly median

```
                  peak_month  peak  median
subreddit                                 
memes                2022-03  33.8     8.2
teenagers            2026-07  18.2     4.2
books                2025-12  12.3     5.9
explainlikeimfive    2012-10  14.8     5.4
todayilearned        2022-08  18.4    11.6
nosurf               2020-12   6.8     3.1
```

### event effects (post minus pre) with placebo p, all groups and outcomes

```
         group                                  event       outcome   effect  placebo_sd       p  placebo_lo  placebo_hi
0   short_form             COVID-19 pandemic declared     sentiment   0.0081      0.0114  0.4400     -0.0230      0.0219
1   short_form             COVID-19 pandemic declared     neg_share   0.0009      0.0121  0.9275     -0.0246      0.0213
2   short_form             COVID-19 pandemic declared    covid_rate   8.1622      1.1886  0.0050     -3.0242      1.4088
3   short_form             COVID-19 pandemic declared   crisis_rate   4.0161      2.5776  0.1150     -4.6150      5.6554
4   short_form  Russia full-scale invasion of Ukraine     sentiment  -0.0155      0.0114  0.1500     -0.0230      0.0219
5   short_form  Russia full-scale invasion of Ukraine     neg_share   0.0189      0.0121  0.1075     -0.0246      0.0213
6   short_form  Russia full-scale invasion of Ukraine  ukraine_rate  56.4221      1.0716  0.0000     -2.1017      2.6154
7   short_form  Russia full-scale invasion of Ukraine   crisis_rate  32.3059      2.5776  0.0000     -4.6150      5.6554
8   short_form         Hamas attack / Gaza war begins     sentiment  -0.0035      0.0114  0.7150     -0.0230      0.0219
9   short_form         Hamas attack / Gaza war begins     neg_share   0.0072      0.0121  0.4550     -0.0246      0.0213
10  short_form         Hamas attack / Gaza war begins     gaza_rate   5.6027      1.0882  0.0050     -1.5060      2.9943
11  short_form         Hamas attack / Gaza war begins   crisis_rate   6.4222      2.5776  0.0300     -4.6150      5.6554
12  short_form          Assassination of Charlie Kirk     sentiment  -0.0102      0.0114  0.3225     -0.0230      0.0219
13  short_form          Assassination of Charlie Kirk     neg_share  -0.0072      0.0121  0.4550     -0.0246      0.0213
14  short_form          Assassination of Charlie Kirk     kirk_rate   4.1168      0.1501  0.0000     -0.2868      0.4416
15  short_form          Assassination of Charlie Kirk   crisis_rate   7.7143      2.5776  0.0150     -4.6150      5.6554
16   long_form             COVID-19 pandemic declared     sentiment   0.0074      0.0208  0.7250     -0.0410      0.0469
17   long_form             COVID-19 pandemic declared     neg_share  -0.0092      0.0140  0.5150     -0.0311      0.0266
18   long_form             COVID-19 pandemic declared    covid_rate   4.5931      0.2805  0.0000     -0.7424      0.6232
19   long_form             COVID-19 pandemic declared   crisis_rate   4.8389      1.7566  0.0150     -2.9375      4.4961
20   long_form  Russia full-scale invasion of Ukraine     sentiment  -0.0383      0.0208  0.0650     -0.0410      0.0469
21   long_form  Russia full-scale invasion of Ukraine     neg_share   0.0253      0.0140  0.0700     -0.0311      0.0266
22   long_form  Russia full-scale invasion of Ukraine  ukraine_rate   2.0958      0.9163  0.0300     -1.5664      1.6967
23   long_form  Russia full-scale invasion of Ukraine   crisis_rate   3.4005      1.7566  0.0550     -2.9375      4.4961
24   long_form         Hamas attack / Gaza war begins     sentiment  -0.0266      0.0208  0.1800     -0.0410      0.0469
25   long_form         Hamas attack / Gaza war begins     neg_share   0.0119      0.0140  0.3800     -0.0311      0.0266
26   long_form         Hamas attack / Gaza war begins     gaza_rate   3.9330      0.5558  0.0000     -1.2221      1.0395
27   long_form         Hamas attack / Gaza war begins   crisis_rate   5.9044      1.7566  0.0075     -2.9375      4.4961
28   long_form          Assassination of Charlie Kirk     sentiment  -0.0128      0.0208  0.5450     -0.0410      0.0469
29   long_form          Assassination of Charlie Kirk     neg_share   0.0050      0.0140  0.7050     -0.0311      0.0266
30   long_form          Assassination of Charlie Kirk     kirk_rate   2.0148      0.0858  0.0000     -0.1527      0.1890
31   long_form          Assassination of Charlie Kirk   crisis_rate  -0.8376      1.7566  0.6025     -2.9375      4.4961
32    baseline             COVID-19 pandemic declared     sentiment   0.0185      0.0188  0.2700     -0.0366      0.0437
33    baseline             COVID-19 pandemic declared     neg_share  -0.0111      0.0166  0.4375     -0.0370      0.0284
34    baseline             COVID-19 pandemic declared    covid_rate   3.9980      0.5214  0.0000     -0.7405      0.9141
35    baseline             COVID-19 pandemic declared   crisis_rate   1.2790      3.6608  0.7300     -7.0985      8.2998
36    baseline  Russia full-scale invasion of Ukraine     sentiment  -0.0441      0.0188  0.0375     -0.0366      0.0437
37    baseline  Russia full-scale invasion of Ukraine     neg_share   0.0198      0.0166  0.2200     -0.0370      0.0284
38    baseline  Russia full-scale invasion of Ukraine  ukraine_rate   0.4153      1.3671  0.7550     -2.3739      3.0344
39    baseline  Russia full-scale invasion of Ukraine   crisis_rate   2.0505      3.6608  0.5275     -7.0985      8.2998
40    baseline         Hamas attack / Gaza war begins     sentiment  -0.0009      0.0188  0.9575     -0.0366      0.0437
41    baseline         Hamas attack / Gaza war begins     neg_share   0.0120      0.0166  0.4175     -0.0370      0.0284
42    baseline         Hamas attack / Gaza war begins     gaza_rate  -0.6385      1.5294  0.4075     -3.7537      2.8312
43    baseline         Hamas attack / Gaza war begins   crisis_rate  -5.2550      3.6608  0.1475     -7.0985      8.2998
44    baseline          Assassination of Charlie Kirk     sentiment  -0.0000      0.0188  1.0000     -0.0366      0.0437
45    baseline          Assassination of Charlie Kirk     neg_share   0.0033      0.0166  0.8350     -0.0370      0.0284
46    baseline          Assassination of Charlie Kirk     kirk_rate   0.2876      0.2258  0.2075     -0.4637      0.3951
47    baseline          Assassination of Charlie Kirk   crisis_rate   4.7605      3.6608  0.1875     -7.0985      8.2998
48  reflective             COVID-19 pandemic declared     sentiment  -0.0365      0.0278  0.1800     -0.0488      0.0464
49  reflective             COVID-19 pandemic declared     neg_share   0.0208      0.0179  0.2275     -0.0395      0.0278
50  reflective             COVID-19 pandemic declared    covid_rate   6.3197      0.5188  0.0000     -1.0633      1.2681
51  reflective             COVID-19 pandemic declared   crisis_rate   4.4836      1.1309  0.0000     -2.4176      2.4528
52  reflective  Russia full-scale invasion of Ukraine     sentiment  -0.0149      0.0278  0.5725     -0.0488      0.0464
53  reflective  Russia full-scale invasion of Ukraine     neg_share   0.0039      0.0179  0.8300     -0.0395      0.0278
54  reflective  Russia full-scale invasion of Ukraine  ukraine_rate   5.0136      0.2895  0.0000     -0.4941      0.7960
55  reflective  Russia full-scale invasion of Ukraine   crisis_rate   3.7324      1.1309  0.0075     -2.4176      2.4528
56  reflective         Hamas attack / Gaza war begins     sentiment  -0.0495      0.0278  0.0400     -0.0488      0.0464
57  reflective         Hamas attack / Gaza war begins     neg_share   0.0369      0.0179  0.0450     -0.0395      0.0278
58  reflective         Hamas attack / Gaza war begins     gaza_rate   5.0310      0.3119  0.0000     -0.7309      0.5978
59  reflective         Hamas attack / Gaza war begins   crisis_rate   9.5118      1.1309  0.0000     -2.4176      2.4528
60  reflective          Assassination of Charlie Kirk     sentiment  -0.0532      0.0278  0.0325     -0.0488      0.0464
61  reflective          Assassination of Charlie Kirk     neg_share   0.0371      0.0179  0.0425     -0.0395      0.0278
62  reflective          Assassination of Charlie Kirk     kirk_rate   5.1945      0.0623  0.0000     -0.1345      0.1450
63  reflective          Assassination of Charlie Kirk   crisis_rate   4.7340      1.1309  0.0000     -2.4176      2.4528
```

### r/nosurf doomscroll rate (mean per 10,000) and event effects

```
                                   event  effect      p  baseline
0             COVID-19 pandemic declared   0.000  1.000     1.586
1  Russia full-scale invasion of Ukraine   0.826  0.052     1.586
2         Hamas attack / Gaza war begins   0.445  0.162     1.586
3          Assassination of Charlie Kirk  -0.249  0.285     1.586
```

### lead-lag with the World Uncertainty Index

```
        group    outcome  r_lag0  best_lag  best_r    n  noise_band
0  short_form  sentiment   -0.01         3    0.15  163        0.15
1  short_form     crisis   -0.01        -5   -0.14  163        0.15
2   long_form  sentiment   -0.07        -5    0.18  163        0.15
3   long_form     crisis   -0.07        -6    0.15  163        0.15
4    baseline  sentiment   -0.00         5    0.19  163        0.15
5    baseline     crisis   -0.09        -5   -0.11  163        0.15
6  reflective  sentiment   -0.03        -2   -0.12  163        0.15
7  reflective     crisis    0.08        -2   -0.11  163        0.15
```

### r/nosurf sessions around events

```
                                   event  sessions_pre  sessions_post  multi_pre  multi_post  median_min_pre  median_min_post
0             COVID-19 pandemic declared          4455           1982      0.115       0.114             6.0              6.0
1  Russia full-scale invasion of Ukraine          5680           2420      0.139       0.119             6.0              9.0
2         Hamas attack / Gaza war begins          5938           3051      0.125       0.133             6.0              7.0
3          Assassination of Charlie Kirk          9078           5203      0.170       0.160             6.0              6.0
```

### change-points in monthly VADER

```
                                                          change_points
subreddit                                                              
memes                                                           2014-08
teenagers          2013-09, 2014-04, 2017-01, 2021-11, 2024-10, 2026-03
books                                         2013-08, 2017-12, 2023-02
explainlikeimfive                                      2017-06, 2022-08
todayilearned                                                   2017-03
nosurf                               2017-01, 2017-08, 2021-10, 2023-12
```

### brainrot terms around events, per 10,000 words (pooled six subreddits)

```
                                                   pre   post  change  hits_post  placebo_p
event                                 term                                                 
COVID-19 pandemic declared            rizz       0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine rizz       0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        rizz       0.125  0.102  -0.023         15      0.563
Assassination of Charlie Kirk         rizz       0.055  0.036  -0.020          7      0.610
COVID-19 pandemic declared            skibidi    0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine skibidi    0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        skibidi    0.024  0.082   0.057         12      0.240
Assassination of Charlie Kirk         skibidi    0.067  0.046  -0.021          9      0.447
COVID-19 pandemic declared            gyatt      0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine gyatt      0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        gyatt      0.006  0.048   0.042          7      0.000
Assassination of Charlie Kirk         gyatt      0.006  0.010   0.004          2      0.443
COVID-19 pandemic declared            brain rot  0.011  0.000  -0.011          0      0.857
Russia full-scale invasion of Ukraine brain rot  0.000  0.015   0.015          2      0.780
Hamas attack / Gaza war begins        brain rot  0.028  0.027  -0.000          4      1.000
Assassination of Charlie Kirk         brain rot  0.225  0.259   0.035         51      0.540
COVID-19 pandemic declared            tung tung  0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine tung tung  0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        tung tung  0.000  0.000   0.000          0      1.000
Assassination of Charlie Kirk         tung tung  0.003  0.005   0.002          1      0.213
COVID-19 pandemic declared            mewing     0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine mewing     0.007  0.007   0.001          1      0.747
Hamas attack / Gaza war begins        mewing     0.000  0.007   0.007          1      0.457
Assassination of Charlie Kirk         mewing     0.000  0.020   0.020          4      0.103
```

### brainrot terms around events, per 10,000 words (memes, teenagers)

```
                                                   pre   post  change  hits_post  placebo_p
event                                 term                                                 
COVID-19 pandemic declared            rizz       0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine rizz       0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        rizz       0.715  0.676  -0.039         15      0.783
Assassination of Charlie Kirk         rizz       0.223  0.211  -0.012          7      0.937
COVID-19 pandemic declared            skibidi    0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine skibidi    0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        skibidi    0.128  0.541   0.412         12      0.200
Assassination of Charlie Kirk         skibidi    0.319  0.272  -0.047          9      0.553
COVID-19 pandemic declared            gyatt      0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine gyatt      0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        gyatt      0.037  0.225   0.189          5      0.023
Assassination of Charlie Kirk         gyatt      0.016  0.060   0.044          2      0.283
COVID-19 pandemic declared            brain rot  0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine brain rot  0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        brain rot  0.073  0.045  -0.028          1      0.827
Assassination of Charlie Kirk         brain rot  0.382  0.785   0.403         26      0.207
COVID-19 pandemic declared            tung tung  0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine tung tung  0.000  0.000   0.000          0      1.000
Hamas attack / Gaza war begins        tung tung  0.000  0.000   0.000          0      1.000
Assassination of Charlie Kirk         tung tung  0.016  0.030   0.014          1      0.113
COVID-19 pandemic declared            mewing     0.000  0.000   0.000          0      1.000
Russia full-scale invasion of Ukraine mewing     0.024  0.000  -0.024          0      0.563
Hamas attack / Gaza war begins        mewing     0.000  0.045   0.045          1      0.443
Assassination of Charlie Kirk         mewing     0.000  0.121   0.121          4      0.123
```

### short-form comments per day: 3 months before vs 3 months after the event month

```
                                         before     after  change_pct
event                                                                
COVID-19 pandemic declared             116093.1  150821.5        29.9
Russia full-scale invasion of Ukraine  130873.5  106335.4       -18.7
Hamas attack / Gaza war begins          47431.1   37496.3       -20.9
Assassination of Charlie Kirk           33981.4   33241.9        -2.2
```

### brainrot per 10,000 words (memes + teenagers): top months

```
month
2023-11-01    4.61
2024-04-01    3.28
2023-12-01    3.20
2025-01-01    2.90
2024-07-01    2.74
2024-06-01    2.66
```

### top terms (hits) in the chosen months

```
         rizz  skibidi  gyatt  fanum tax  rizzler  mewing  brain rot  brainrot
2023-10  16.0     15.0    5.0        4.0      NaN     NaN        NaN       NaN
2023-11  18.0     64.0   19.0        NaN     10.0     NaN        NaN       NaN
2024-04  20.0     22.0    NaN        NaN      NaN    14.0        6.0       NaN
2024-12   7.0     24.0    NaN        NaN      NaN     NaN        3.0       6.0
2025-01   8.0     12.0    NaN        NaN      NaN     NaN       14.0      37.0
```

### brainrot-hit comments mentioning a topic, chosen months

```
         hit comments  gaza/israel/palestine/hamas  war  iran  tiktok  ban  oxford/word of the year
month                                                                                              
2023-10            32                            0    0     0       0    0                        0
2023-11            91                            0    1     0       4    0                        0
2024-04            59                            0    0     0       3    0                        0
2024-12            40                            0    0     0       3    0                        0
2025-01            64                            0    0     0      12    4                        0
```

### crisis words per 10,000 (memes + teenagers), 2023-08 to 2025-02 (median of all months 6.0)

```
month
2023-08-01     4.6
2023-09-01     5.6
2023-10-01    10.4
2023-11-01     6.3
2023-12-01     7.7
2024-01-01     9.0
2024-02-01     7.9
2024-03-01     8.6
2024-04-01    10.7
2024-05-01     9.2
2024-06-01     8.4
2024-07-01     7.2
2024-08-01     8.8
2024-09-01     5.1
2024-10-01     7.3
2024-11-01     5.8
2024-12-01    10.8
2025-01-01     6.5
2025-02-01     8.4
```

### all brainrot words pooled, rate per 10,000 words: 8 weeks before vs 4 / 8 weeks after (placebo: 888 days)

```
                                                              before  after  change  hits_after  placebo_p  placebo_lo  placebo_hi
subreddits        event                          weeks_after                                                                      
memes + teenagers Hamas attack / Gaza war begins 4             0.953  1.532   0.579          34      0.407      -1.382       1.946
                  Assassination of Charlie Kirk  4             0.956  1.479   0.524          49      0.439      -1.382       1.946
                  Hamas attack / Gaza war begins 8             0.953  3.396   2.443         166      0.000      -1.410       1.414
                  Assassination of Charlie Kirk  8             0.956  1.112   0.156          57      0.694      -1.410       1.414
all six           Hamas attack / Gaza war begins 4             0.184  0.266   0.082          39      0.548      -0.349       0.512
                  Assassination of Charlie Kirk  4             0.356  0.376   0.020          74      0.860      -0.349       0.512
                  Hamas attack / Gaza war begins 8             0.184  0.563   0.379         178      0.035      -0.352       0.386
                  Assassination of Charlie Kirk  8             0.356  0.368   0.012         126      0.925      -0.352       0.386
```

### memes + teenagers, weekly rate per 10,000 words around each event (week 0 = event week)

```
     Hamas attack / Gaza war begins  Assassination of Charlie Kirk
-8                             0.74                           1.56
-7                             0.94                           0.45
-6                             1.65                           0.68
-5                             0.91                           0.33
-4                             0.43                           1.94
-3                             1.01                           1.93
-2                             1.61                           0.28
-1                             0.65                           0.93
 0                             0.47                           0.53
 1                             3.12                           0.83
 2                             0.51                           0.64
 3                             1.58                           2.66
 4                             0.53                            NaN
 5                             4.45                            NaN
 6                            11.00                            NaN
 7                             5.36                            NaN
 8                             3.01                            NaN
 9                             2.08                            NaN
 10                            4.17                            NaN
 11                            1.91                            NaN
 12                            3.34                            NaN
```

### the highest week after the Gaza war (week 6, from 2023-11-18): sampled comments with brainrot words

```
      comments_with_brainrot  authors  days
week                                       
6                         25       24     3
```

### r/nosurf doomscroll mentions per 10,000 words, by year

```
day
2019    0.00
2020    0.08
2021    0.29
2022    0.66
2023    1.14
2024    1.88
2025    3.24
2026    4.95
```

### r/nosurf doomscroll, 4-week rolling rate: latest and maximum

```
latest        3.835027
max           6.291073
max_week    2026-07-19
```

### r/nosurf daily rhythm: largest cell shift per event (pp) and the 95th percentile at random dates

```
COVID-19 pandemic declared               0.56
Russia full-scale invasion of Ukraine    0.50
Hamas attack / Gaza war begins           0.37
Assassination of Charlie Kirk            0.77
95% of random dates stay under           0.82
```

### r/nosurf sessions (2+ messages): share by length bucket, before vs after

```
                                      before                        after                       
bucket                                 1 min 10-29   2-4  30+   5-9 1 min 10-29   2-4  30+   5-9
event                                                                                           
Assassination of Charlie Kirk           21.5  30.3  21.1  8.1  19.1  23.0  31.1  22.0  8.2  15.7
COVID-19 pandemic declared              20.0  34.4  22.9  4.9  17.8  22.2  31.1  22.2  6.7  17.8
Hamas attack / Gaza war begins          20.1  30.0  24.2  5.2  20.5  19.5  30.6  22.0  6.7  21.2
Russia full-scale invasion of Ukraine   21.3  30.2  21.2  8.5  18.9  17.1  39.4  17.4  6.6  19.5
```

### same r/nosurf authors: change in mean tone (random-date 95% range -0.063 to +0.058)

```
                                       authors  mean_change  ci_low  ci_high
event                                                                       
COVID-19 pandemic declared                 322       -0.037  -0.086    0.025
Russia full-scale invasion of Ukraine      401       -0.042  -0.094    0.008
Hamas attack / Gaza war begins             385       -0.058  -0.112   -0.006
Assassination of Charlie Kirk              613       -0.070  -0.115   -0.024
```

### r/nosurf sessions: bucket that moved most per event (largest gap 9.2 points after Russia full-scale invasion of Ukraine, placebo p = 0.02; largest gap at the other events 3.3)

```
                                      bucket  before  after  gap
event                                                           
COVID-19 pandemic declared             10-29    34.4   31.1  3.3
Russia full-scale invasion of Ukraine  10-29    30.2   39.4  9.2
Hamas attack / Gaza war begins           2-4    24.2   22.0  2.3
Assassination of Charlie Kirk            5-9    19.1   15.7  3.3
```
