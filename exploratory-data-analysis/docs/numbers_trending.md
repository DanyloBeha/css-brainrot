# Numbers behind the YouTube trending daily table

Written by `python -m src.trending` (numeric tables only; row-level text is never saved).
Table: `data/external/youtube_trending_daily.parquet` (45,386 rows). Definitions are in the docstring of `src/trending.py`.

### rows loaded per file next to an independent count (must be equal)

```
                rows_loaded  rows_pandas
file                                    
CA                   268742       268742
GB                   268791       268791
IN                   251277       251277
US                   268787       268787
keshavbansal95       449791       449791
```

### US columns rebuilt with pandas vs the table (days where the table is empty are skipped)

```
                    n_videos  views_snapshot  views_new  br_n_videos
days_compared         1323.0          1323.0     1323.0       1323.0
max_abs_difference       0.0             0.0        0.0          0.0
```

### sources: rows, unique videos, countries, dates (no_date and no_views rows are left out of the table)

```
                   rows  unique_videos  countries  no_date  no_views  first_day   last_day  days_with_list  days_no_list
source                                                                                                                  
keshavbansal95   449791          37457        110        0         5 2024-10-12 2025-09-26             348             2
rsrishav        1057597         158416          4        0         0 2020-08-12 2024-04-15            1323            20
```

### gap between the sources (empty rows, not zeros)

```
    first_day    last_day  days
0  2024-04-16  2024-10-11   179
```

### unique videos and days with a list, per source and country (entries = rows of the source file)

```
                                       entries  unique_videos  brainrot_videos  brainrot_excl_game  days_with_list   first_day    last_day
source         country                                                                                                                    
keshavbansal95 India                     42249          17103              318                 159             348  2024-10-12  2025-09-26
               Spain                     18519           6828              278                 129             348  2024-10-12  2025-09-26
               United Kingdom            12688           3908               69                  16             348  2024-10-12  2025-09-26
               Chile                      7145           3150              340                 138             347  2024-10-12  2025-09-26
               Argentina                  6773           2930              394                 167             348  2024-10-12  2025-09-26
               Venezuela                  7518           2889              348                 158             348  2024-10-12  2025-09-26
               Colombia                   7163           2793              294                 136             348  2024-10-12  2025-09-26
               Nepal                     19061           2507              184                  84             348  2024-10-12  2025-09-26
               Mexico                     6054           2343              285                 131             348  2024-10-12  2025-09-26
               Peru                       6373           2319              356                 158             348  2024-10-12  2025-09-26
               Ecuador                    6794           2317              349                 154             348  2024-10-12  2025-09-26
               Pakistan                  17599           2306              235                 101             348  2024-10-12  2025-09-26
               Canada                     8291           2124               37                   8             348  2024-10-12  2025-09-26
               Australia                  9995           2120               26                   7             348  2024-10-12  2025-09-26
               Dominican Republic         6227           1777              253                 128             348  2024-10-12  2025-09-26
               Bolivia                    6673           1708              264                 132             348  2024-10-12  2025-09-26
               United States              6372           1618               41                  10             348  2024-10-12  2025-09-26
               Papua New Guinea           6371           1618               41                  10             348  2024-10-12  2025-09-26
               United Arab Emirates       6974           1402               18                   6             348  2024-10-12  2025-09-26
               Guatemala                  6259           1393              194                 100             348  2024-10-12  2025-09-26
               Bangladesh                 8319           1376               86                  51             348  2024-10-12  2025-09-26
               Paraguay                   6911           1270              205                 100             348  2024-10-12  2025-09-26
               Honduras                   6282           1140              156                  84             348  2024-10-12  2025-09-26
               Costa Rica                 6575           1056              122                  64             348  2024-10-12  2025-09-26
               Uruguay                    6432            944              141                  61             348  2024-10-12  2025-09-26
               Sri Lanka                  8466            814               11                  10             348  2024-10-12  2025-09-26
               Nicaragua                  5197            780              115                  64             348  2024-10-12  2025-09-26
               Germany                    3586            743                9                   3             348  2024-10-12  2025-09-26
               Ireland                    8068            735               10                   1             348  2024-10-12  2025-09-26
               Saudi Arabia               3621            725               11                   2             348  2024-10-12  2025-09-26
               Panama                     5117            688               74                  42             348  2024-10-12  2025-09-26
               Singapore                  6843            646                7                   2             348  2024-10-12  2025-09-26
               El Salvador                4391            629               77                  44             348  2024-10-12  2025-09-26
               Algeria                    1800            615                5                   5             338  2024-10-12  2025-09-26
               Kenya                      4494            614                4                   1             348  2024-10-12  2025-09-26
               Egypt                      1991            609               13                   3             348  2024-10-12  2025-09-26
               Iraq                       1863            588                7                   2             348  2024-10-12  2025-09-26
               Sweden                     3333            550                8                   0             348  2024-10-12  2025-09-26
               Iceland                    7644            548                1                   1             348  2024-10-12  2025-09-26
               Morocco                    1814            480               12                   3             348  2024-10-12  2025-09-26
               Nigeria                    4080            454                1                   0             348  2024-10-12  2025-09-26
               Norway                     4100            450                6                   0             348  2024-10-12  2025-09-26
               Indonesia                  2573            438               11                  11             344  2024-10-12  2025-09-26
               Netherlands                2334            420                4                   1             348  2024-10-12  2025-09-26
               Denmark                    3172            415                5                   0             348  2024-10-12  2025-09-26
               Kuwait                     4194            414                0                   0             347  2024-10-12  2025-09-26
               New Zealand                4805            405                9                   0             348  2024-10-12  2025-09-26
               Austria                    3662            391                3                   1             348  2024-10-12  2025-09-26
               South Africa               2365            389                3                   0             346  2024-10-12  2025-09-26
               Qatar                      3815            372                0                   0             348  2024-10-12  2025-09-26
               Uganda                     3336            363                0                   0             348  2024-10-12  2025-09-26
               France                     1664            358                1                   1             343  2024-10-12  2025-09-26
               Ghana                      3657            351                0                   0             348  2024-10-12  2025-09-26
               Zimbabwe                   3756            350                0                   0             348  2024-10-12  2025-09-26
               Italy                      1346            333                2                   1             323  2024-10-13  2025-09-26
               Puerto Rico                3011            329                9                   8             348  2024-10-12  2025-09-26
               Russia                      714            305                8                   8             305  2024-10-12  2025-09-26
               Finland                    2720            292                4                   0             348  2024-10-12  2025-09-26
               Philippines                1610            291                9                   3             323  2024-10-18  2025-09-26
               Malta                      5376            289                1                   1             348  2024-10-12  2025-09-26
               Malaysia                   2041            264                4                   2             318  2024-10-20  2025-09-26
               Belgium                    1990            246                4                   0             335  2024-10-21  2025-09-26
               Greece                     2224            244                5                   1             338  2024-10-22  2025-09-26
               Oman                       3360            237                0                   0             348  2024-10-12  2025-09-26
               Tanzania                   2575            229                0                   0             348  2024-10-12  2025-09-26
               Brazil                      654            219                9                   6             288  2024-10-12  2025-09-26
               Cambodia                   2001            203                4                   4             348  2024-10-12  2025-09-26
               Thailand                    604            197                7                   7             267  2024-10-19  2025-09-26
               Switzerland                2552            195                1                   0             348  2024-10-12  2025-09-26
               Liechtenstein              2553            195                1                   0             348  2024-10-12  2025-09-26
               Luxembourg                 3219            190                0                   0             330  2024-10-12  2025-09-26
               Senegal                    2360            188                0                   0             347  2024-10-12  2025-09-26
               Laos                       1474            169                2                   2             341  2024-10-12  2025-09-26
               Portugal                   1353            159                1                   0             287  2024-10-22  2025-09-26
               Jamaica                    1622            147                3                   0             319  2024-10-12  2025-09-26
               Estonia                    3205            145                1                   1             348  2024-10-12  2025-09-26
               Bahrain                    2505            145                0                   0             347  2024-10-12  2025-09-26
               Cyprus                     2372            142                0                   0             348  2024-10-12  2025-09-26
               Croatia                    1835            140                3                   0             347  2024-10-12  2025-09-26
               Romania                    1001            136                5                   2             329  2024-10-21  2025-09-26
               Israel                     1277            134                3                   0             342  2024-10-17  2025-09-26
               Hong Kong                  1056            126                3                   2             313  2024-10-20  2025-09-26
               Lithuania                  1715            122                4                   0             348  2024-10-12  2025-09-26
               Czechia                    1067            120                2                   2             314  2024-10-19  2025-09-26
               Slovenia                   2317            115                1                   1             348  2024-10-12  2025-09-26
               Hungary                    1352            107                0                   0             337  2024-10-19  2025-09-26
               Libya                      1003            107                0                   0             327  2024-10-12  2025-09-26
               Jordan                     1111            105                3                   0             348  2024-10-12  2025-09-26
               Bulgaria                   1467            105                3                   1             347  2024-10-12  2025-09-26
               Poland                      632            101                1                   1             275  2024-10-12  2025-09-26
               Yemen                      1090             96                0                   0             331  2024-10-12  2025-09-26
               Slovakia                   1395             94                2                   0             342  2024-10-12  2025-09-26
               Tunisia                    1099             94                0                   0             330  2024-10-12  2025-09-26
               North Macedonia            1697             84                3                   1             348  2024-10-12  2025-09-26
               Serbia                     1063             81                4                   1             345  2024-10-12  2025-09-26
               Georgia                    1293             80                3                   1             341  2024-10-12  2025-09-26
               Ukraine                     464             66                2                   2             239  2024-10-20  2025-09-26
               Latvia                     1295             66                0                   0             348  2024-10-12  2025-09-26
               Lebanon                     707             64                2                   0             316  2024-10-12  2025-09-26
               Turkey                      304             60                1                   1             177  2024-10-12  2025-09-26
               Bosnia and Herzegovina      907             52                3                   1             346  2024-10-12  2025-09-26
               Taiwan                      328             51                2                   2             207  2024-10-19  2025-09-26
               Montenegro                  946             47                1                   1             319  2024-10-12  2025-08-30
               Kazakhstan                  503             45                2                   2             280  2024-10-25  2025-09-26
               Moldova                     699             43                0                   0             308  2024-10-12  2025-09-26
               Vietnam                     185             42                2                   2             132  2025-01-11  2025-09-25
               South Korea                 184             38                2                   2             128  2024-10-12  2025-09-21
               Belarus                     439             33                2                   2             282  2024-10-12  2025-09-26
               Azerbaijan                  362             31                1                   1             221  2024-10-25  2025-09-26
               Japan                       199             30                0                   0             116  2024-12-03  2025-08-03
rsrishav       IN                       251277          78847               44                  44            1323  2020-08-12  2024-04-15
               CA                       268742          50875               61                  61            1323  2020-08-12  2024-04-15
               GB                       268791          47607               63                  63            1323  2020-08-12  2024-04-15
               US                       268787          47142               72                  72            1323  2020-08-12  2024-04-15
```

### pooled series per year: views gained = sum of views_new over the days (millions); snapshot = mean over days of views_snapshot (millions); n_new differs from n_videos, so gained is a lower bound

```
                     days  videos_per_day  snapshot_per_day_M  gained_M  br_videos_per_day  br_snapshot_per_day_M  br_gained_M  brx_gained_M  br_share_gained_%  brx_share_gained_%
source         year                                                                                                                                                                
keshavbansal95 2024    80          373.66             2611.93   8731.12               1.06                   4.79         9.59          9.59               0.11                0.11
               2025   268           502.5              2308.9  25541.37               11.2                   7.84       133.19         86.51               0.52                0.34
rsrishav       2020   138          535.85             1080.16  15716.33                0.0                    0.0          0.0           0.0                0.0                 0.0
               2021   353          540.48             1357.83  55509.92                0.0                    0.0          0.0           0.0                0.0                 0.0
               2022   364          542.85             1194.59  52386.77                0.0                    0.0          0.0           0.0                0.0                 0.0
               2023   362          518.92             1053.41  32948.59                1.5                   25.7       581.74        581.74               1.77                1.77
               2024   106          505.93             1133.92   8387.19               1.31                  22.79       161.51        161.51               1.93                1.93
```

### days with data and days with no brainrot-titled video on the pooled list (br = with the game, brx = without)

```
                days  zero_br_days  zero_brx_days  zero_br_%  zero_brx_%
source                                                                  
keshavbansal95   348           103            103       29.6        29.6
rsrishav        1323          1047           1047       79.1        79.1
```

### pooled series per quarter: brainrot-titled video-days (a video on the list on 3 days counts 3) per 1,000 list entries

```
                        days  br_zero_days  br_videos  videos  br_gained_M  br_per_1000_videos
source         quarter                                                                        
keshavbansal95 2024Q4     80            23         85   29893         9.59                2.84
               2025Q1     90            60         30   34296         2.46                0.87
               2025Q2     90            19        240   34874         29.6                6.88
               2025Q3     88             1       2731   65500       101.13               41.69
rsrishav       2023Q1     90            83          7   47279         0.74                0.15
               2023Q2     91            61         49   47701         9.88                1.03
               2023Q3     89             0        347   45848        346.8                7.57
               2023Q4     92            22        141   47021       224.32                 3.0
               2024Q1     91            26         94   46325       129.47                2.03
               2024Q2     15             0         45    7304        32.04                6.16
```

### peak days by views gained, brainrot-titled, game included (millions; pooled series; n_negative > 0 or one video carrying the day = see the largest changes)

```
                       day  n_videos  n_new  n_negative  br_n_videos  brx_n_videos  share_of_all_new  br_views_new_M  max_single_video_M
source                                                                                                                                  
keshavbansal95  2025-09-07       849    609           4           51            15            0.0512            3.04                3.78
keshavbansal95  2025-04-24       370    314           0            6             6            0.0342            2.76                11.0
keshavbansal95  2025-08-23       828    574           4           32            19            0.0315             2.3                9.87
keshavbansal95  2025-09-05       842    531           2           43            18              0.04            2.24                4.56
keshavbansal95  2025-08-02       817    547           3           46            28            0.0383            2.16                4.75
keshavbansal95  2025-08-13       920    604           4           37            12            0.0212            2.13               23.28
rsrishav        2023-11-15       502    390           0            3             3            0.1518            16.2               16.13
rsrishav        2023-09-04       522    393           1            4             4            0.1283           13.88               16.15
rsrishav        2023-12-30       539    396           0            2             2            0.2019           12.22               10.84
rsrishav        2023-09-30       505    417           0            2             2            0.1062           11.24                11.2
rsrishav        2024-01-27       469    395           2            1             1            0.1492           10.82               10.82
rsrishav        2023-08-20       528    401           0            6             6            0.1175           10.63                6.22
```

### peak days by views gained, brainrot-titled, game excluded (millions; pooled series; n_negative > 0 or one video carrying the day = see the largest changes)

```
                       day  n_videos  n_new  n_negative  br_n_videos  brx_n_videos  share_of_all_new  brx_views_new_M  max_single_video_M
source                                                                                                                                   
keshavbansal95  2025-04-24       370    314           0            6             6            0.0342             2.76                11.0
keshavbansal95  2024-10-20       374    307           1            2             2            0.0151             1.87                7.55
keshavbansal95  2025-09-07       849    609           4           51            15            0.0296             1.76                3.78
keshavbansal95  2025-08-23       828    574           4           32            19            0.0215             1.57                9.87
keshavbansal95  2025-08-04       863    574           2           42            26            0.0322             1.53                2.44
keshavbansal95  2025-06-24       387    347           1            2             2            0.0145             1.47               12.01
rsrishav        2023-11-15       502    390           0            3             3            0.1518             16.2               16.13
rsrishav        2023-09-04       522    393           1            4             4            0.1283            13.88               16.15
rsrishav        2023-12-30       539    396           0            2             2            0.2019            12.22               10.84
rsrishav        2023-09-30       505    417           0            2             2            0.1062            11.24                11.2
rsrishav        2024-01-27       469    395           2            1             1            0.1492            10.82               10.82
rsrishav        2023-08-20       528    401           0            6             6            0.1175            10.63                6.22
```

### peak days by views gained, all videos (millions; pooled series; n_negative > 0 or one video carrying the day = see the largest changes)

```
                       day  n_videos  n_new  n_negative  br_n_videos  brx_n_videos  views_new_M  max_single_video_M
source                                                                                                             
keshavbansal95  2024-12-11       383    299           0            0             0       175.09               29.11
keshavbansal95  2024-11-30       393    284           0            0             0       174.96               21.71
keshavbansal95  2025-03-16       446    369           2            0             0       167.33               16.46
keshavbansal95  2024-12-07       386    313           0            1             1       166.59               14.09
keshavbansal95  2025-03-15       431    368           0            0             0       161.97               24.42
keshavbansal95  2025-02-01       382    325           0            1             1       161.21               14.05
rsrishav        2024-04-03       493    395           0            3             3       869.82              778.92
rsrishav        2021-07-10       546    429           2            0             0       287.34                60.9
rsrishav        2022-09-10       544    450           0            0             0       286.74                39.5
rsrishav        2021-07-08       593    469           2            0             0       285.34               29.09
rsrishav        2021-07-11       532    387           1            0             0       270.97               41.99
rsrishav        2021-05-17       499    369           1            0             0       266.12               31.56
```

### views_new: video-days with and without a day-over-day change, negative changes (kept in the sums), merged_entries (same video twice on one day in a list, or in several countries when pooled; highest count kept)

```
                            video_days  with_new  first_ever  back_after_absence  negative  negative_sum  most_negative       new_sum  zero  merged_entries  negative_%_of_new
level       source                                                                                                                                                            
per country keshavbansal95      449786    350890       94236                4660      1235     -12794910        -336612  138903262018    73               0             0.3520
            rsrishav           1042532    800021      224471               18040      2507   -2903095614    -1403538648  267382663306   186           15065             0.3134
pooled      keshavbansal95      164563    125808       37456                1299       583      -4274473        -336612   34272490493    37          285223             0.4634
            rsrishav            703815    536968      158416                8431      1551   -1460005868    -1403538648  164948799529   101          353782             0.2888
```

### pooled days on which views_new is negative

```
     source        day     views_new
0  rsrishav 2024-04-05 -1.340071e+09
```

### largest single-video day-over-day changes in view count (per country; video ids left out)

```
         country         day      pviews       views         new
source                                                          
rsrishav      GB  2024-04-05  1406329649     2791001 -1403538648
rsrishav      US  2024-04-05  1406329649     2791001 -1403538648
rsrishav      US  2024-04-03   628718636  1407643634   778924998
rsrishav      IN  2020-08-22    57229275   126375269    69145994
rsrishav      GB  2020-08-22    57229275   126375269    69145994
rsrishav      US  2020-08-22    57229275   126375269    69145994
```

### unique brainrot-titled videos: by title (used here), by title or tags, added by tags only

```
                by_title  by_title_or_tags  tags_only
source                                               
keshavbansal95      1081              1333        252
rsrishav             107               140         33
```
