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
3415  2020-04-15 00:00:00     238.0     49.0   59.0        0.25        0.52
1667  2021-02-12 00:00:00     243.0     37.0   41.0        0.17        0.41
1196  2021-12-30 00:00:00     270.0     38.0   89.0        0.33        0.63
2393  2024-01-25 00:00:00     351.0     43.0  112.0        0.32        0.55
1163  2024-03-22 00:00:00     367.0     43.0  122.0        0.33        0.53
286   2024-08-16 00:00:00     342.0     49.0   93.0        0.27        0.55
1317  2024-12-19 00:00:00     382.0     51.0  106.0        0.28        0.46
2333  2025-09-11 00:00:00     530.0     58.0  160.0        0.30        0.72
0                 typical     131.0     33.0    NaN        0.21        0.43
```

### records per year and subreddit (millions)

```
year                          2012  2013  2014  2015  2016  2017  2018   2019   2020   2021   2022   2023   2024  2025  2026
type       subreddit                                                                                                        
comment    books              0.32  0.53  0.84  0.84  0.86  0.99  0.96   0.82   0.87   1.19   1.39   1.31   1.01  0.71  0.50
           explainlikeimfive  0.48  1.13  2.20  2.64  1.93  1.55  1.08   1.05   1.18   1.32   1.53   1.48   1.45  1.18  0.87
           memes              0.01  0.03  0.03  0.02  0.03  0.23  2.80  19.30  34.50  26.04  11.61   5.59   3.46  2.83  2.07
           nosurf             0.00  0.00  0.00  0.00  0.00  0.01  0.02   0.03   0.05   0.05   0.05   0.05   0.07  0.08  0.05
           teenagers          0.56  2.84  2.66  0.97  1.01  2.96  3.94  17.01  17.91  22.33  22.36  12.32  10.66  8.68  7.06
           todayilearned      3.20  5.06  5.61  6.25  5.71  5.75  6.33   5.94   6.24   4.60   3.21   3.49   3.24  2.88  2.42
submission books              0.03  0.04  0.05  0.07  0.08  0.07  0.06   0.05   0.07   0.07   0.07   0.07   0.07  0.07  0.03
           explainlikeimfive  0.04  0.11  0.21  0.26  0.24  0.24  0.14   0.15   0.16   0.12   0.10   0.07   0.07  0.05  0.03
           memes              0.02  0.03  0.02  0.02  0.03  0.08  0.42   2.96   4.31   2.16   0.82   0.46   0.31  0.14  0.08
           nosurf             0.00  0.00  0.00  0.00  0.00  0.00  0.00   0.00   0.01   0.01   0.01   0.01   0.01  0.01  0.01
           teenagers          0.02  0.09  0.13  0.07  0.07  0.23  0.39   1.91   1.96   1.56   1.30   0.81   0.79  0.61  0.37
           todayilearned      0.25  0.26  0.21  0.22  0.20  0.18  0.16   0.15   0.16   0.11   0.07   0.06   0.06  0.05  0.03
```

### share of comments removed/deleted and bot, by year

```
          removed_rows                                                         bot_rows                                                        
subreddit        books explainlikeimfive  memes nosurf teenagers todayilearned    books explainlikeimfive  memes nosurf teenagers todayilearned
year                                                                                                                                           
2012             0.063             0.069  0.088  0.109     0.097         0.081    0.001             0.001  0.004  0.000     0.000         0.001
2013             0.071             0.088  0.091  0.086     0.084         0.080    0.002             0.002  0.044  0.000     0.001         0.002
2014             0.070             0.116  0.089  0.084     0.071         0.073    0.011             0.004  0.071  0.005     0.006         0.005
2015             0.068             0.109  0.084  0.043     0.076         0.060    0.020             0.011  0.075  0.001     0.011         0.002
2016             0.076             0.152  0.086  0.066     0.076         0.064    0.024             0.027  0.050  0.000     0.010         0.003
2017             0.070             0.166  0.068  0.113     0.050         0.061    0.019             0.037  0.019  0.008     0.007         0.003
2018             0.065             0.157  0.058  0.085     0.041         0.059    0.019             0.032  0.092  0.007     0.005         0.003
2019             0.075             0.143  0.096  0.076     0.043         0.062    0.025             0.034  0.064  0.067     0.006         0.003
2020             0.078             0.132  0.130  0.089     0.051         0.072    0.031             0.045  0.047  0.134     0.009         0.003
2021             0.074             0.138  0.112  0.102     0.054         0.085    0.023             0.032  0.036  0.122     0.006         0.003
2022             0.062             0.131  0.091  0.078     0.049         0.075    0.022             0.025  0.030  0.122     0.008         0.003
2023             0.037             0.087  0.075  0.036     0.033         0.058    0.021             0.020  0.057  0.106     0.011         0.002
2024             0.014             0.057  0.058  0.011     0.020         0.035    0.051             0.022  0.058  0.099     0.017         0.002
2025             0.018             0.045  0.060  0.019     0.029         0.033    0.075             0.020  0.013  0.100     0.013         0.002
2026             0.018             0.051  0.067  0.093     0.042         0.036    0.042             0.012  0.009  0.067     0.011         0.001
```

### share of messages written by the top 1% of authors

```
books                0.209
explainlikeimfive    0.240
memes                0.149
nosurf               0.236
teenagers            0.288
todayilearned        0.167
```

### exact comments per submission, 2015 and 2025

```
type                    comment  submission  ratio
subreddit         year                            
books             2015   839226       67023   12.5
                  2025   710877       70197   10.1
explainlikeimfive 2015  2641193      264422   10.0
                  2025  1182312       47974   24.6
memes             2015    20338       15522    1.3
                  2025  2827274      139536   20.3
nosurf            2015     1304         314    4.2
                  2025    81680        7977   10.2
teenagers         2015   969574       65406   14.8
                  2025  8678096      609736   14.2
todayilearned     2015  6248159      217651   28.7
                  2025  2879612       54449   52.9
```

### emoji concentration, r/teenagers 2018-01

```
    emoji   top1    top5  authors  top5_share
0  2497.0  495.0  1531.0     1097        0.61
```

### comment length and very short share (12-month means)

```
                  first_month  len_first  len_low low_month  len_last  short_first  short_peak short_peak_month  short_last
subreddit                                                                                                                  
books                 2012-06       23.7     23.6   2012-07      26.6         10.8        11.1          2014-04         8.1
explainlikeimfive     2012-06       30.2     29.1   2014-11      30.8         10.2        10.3          2013-02         7.0
memes                 2017-01        9.0      5.7   2019-06      11.6         33.0        49.7          2019-09        24.2
nosurf                2017-12       38.6     26.1   2026-07      26.4          8.8        13.3          2020-06        12.7
teenagers             2012-06       15.8      5.2   2022-08       7.2         19.1        50.6          2022-08        40.7
todayilearned         2012-06       15.3     15.1   2018-05      16.4         16.8        18.0          2018-05        14.9
```

### MTLD and Flesch medians, 2012-14 vs 2024-26

```
                   mtld_12_14  mtld_24_26  flesch_12_14  flesch_24_26
subreddit                                                            
books                   109.9       116.2          72.6          70.6
explainlikeimfive        92.5       101.6          67.2          66.5
memes                   129.6       152.8          80.3          74.5
nosurf                   95.6       123.3          72.6          71.1
teenagers               118.2       147.6          80.7          77.8
todayilearned           123.4       137.7          72.0          69.9
```

### VADER 12-month mean: first, peak, last

```
                   first   peak peak_month   last
subreddit                                        
books              0.255  0.266    2013-05  0.170
explainlikeimfive  0.133  0.143    2020-08  0.115
memes              0.055  0.057    2012-09  0.037
nosurf             0.362  0.363    2017-07  0.159
teenagers          0.167  0.167    2012-06  0.052
todayilearned      0.042  0.055    2022-05  0.045
```

### emoji per 10,000 words (12-month mean): max and last

```
                     max   last
subreddit                      
books               11.5   10.1
explainlikeimfive    3.3    3.2
memes              184.1   38.5
nosurf              14.0   14.0
teenagers          399.3  117.3
todayilearned        9.6    9.3
```

### brainrot (core+extended) per 10,000 words: peak month

```
             subreddit      month  per_10k   reach
173              books 2026-06-01   0.3165  0.0012
324  explainlikeimfive 2024-04-01   1.6394  0.0058
441              memes 2023-11-01   6.8952  0.0094
566             nosurf 2025-01-01   1.9566  0.0097
718          teenagers 2022-12-01   5.5168  0.0054
936      todayilearned 2026-05-01   0.2008  0.0003
```

### brainrot per 10,000 words: 2025 mean and last six months

```
                   2025  last6
subreddit                     
books              0.08   0.10
explainlikeimfive  0.02   0.01
memes              1.15   0.36
nosurf             1.17   0.77
teenagers          1.37   0.41
todayilearned      0.04   0.07
```

### reach: peak

```
             subreddit      month     reach  one_in
173              books 2026-06-01  0.001212   825.0
324  explainlikeimfive 2024-04-01  0.005828   172.0
441              memes 2023-11-01  0.009411   106.0
566             nosurf 2025-01-01  0.009671   103.0
737          teenagers 2024-07-01  0.005479   183.0
918      todayilearned 2024-11-01  0.000381  2628.0
```

### core tier per 10,000 words: peak month

```
              subreddit      month  per_10k_words
692               books 2026-06-01          0.317
1296  explainlikeimfive 2024-04-01          1.466
1984              memes 2023-11-01          4.243
2748             nosurf 2025-01-01          1.881
3432          teenagers 2024-07-01          3.287
4156      todayilearned 2024-11-01          0.103
```

### extended tier per 10,000 words: peak month

```
              subreddit      month  per_10k_words
625               books 2025-01-01          0.102
1297  explainlikeimfive 2024-04-01          0.174
1985              memes 2023-11-01          2.652
2729             nosurf 2024-08-01          0.183
3357          teenagers 2022-12-01          5.416
4125      todayilearned 2024-03-01          0.134
```

### term shares by year (%) and hits per year

```
      brain rot  brainrot  gyatt  other  rizz  skibidi  tung tung    hits
year                                                                     
2022        7.0       4.0    1.0    6.0  83.0      0.0        0.0   103.0
2023        8.0       4.0    9.0    4.0  52.0     23.0        0.0   541.0
2024       24.0      17.0    5.0    4.0  19.0     31.0        0.0  1092.0
2025       34.0      38.0    2.0    2.0  12.0     12.0        0.0   942.0
2026       42.0      41.0    0.0    1.0   7.0      5.0        3.0   409.0
```

### log-odds words, short_form

```
       gained     lost
0         bro   school
1       women  friends
2         men   really
3   literally     haha
4        game  college
5      people     edit
6       trans   thanks
7         idk    class
8          ur   pretty
9        real  awesome
10      human     year
11      woman   friend
```

### log-odds words, long_form

```
        gained        lost
0          lol        edit
1           ai      thanks
2     finished     awesome
3        water  government
4      started        wage
5      romance     ender's
6       energy          tl
7    literally      amazon
8         heat       movie
9   absolutely       great
10        lmao      pretty
11       speed     minimum
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
