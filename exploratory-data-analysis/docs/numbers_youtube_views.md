# Numbers behind the YouTube views chart

Written by `python -m src.yt_views` (numeric tables only).

### videos in the sample (pages with data)

```
   videos  brainrot_title  game_in_title  brainrot_excl_game  found_by_views_sort
0    9949            8141           1010                7131                 5108
```

### brainrot videos (no game) left out of the chart: published before 2019, under 1 day old (no per-day rate)

```
   before_2019  under_1_day
0           19          191
```

### brainrot videos (no game) by publish year

```
         n  median_views  median_views_per_day  p10_per_day  p90_per_day
year                                                                    
2019    59       56975.0                  22.0          3.0        713.0
2020    93       55084.0                  24.0          0.0        849.0
2021   145        6877.0                   4.0          0.0        157.0
2022   172         820.0                   1.0          0.0        507.0
2023   891      179937.0                 154.0          0.0       9961.0
2024  1325       53392.0                  63.0          0.0       4154.0
2025  2251      525702.0                1299.0          1.0      17817.0
2026  2176       36594.0                1752.0          3.0      20207.0
```

### same, only videos the views-sorted search found

```
         n  median_views  median_views_per_day
year                                          
2019    50       72504.0                  27.0
2020    61       55084.0                  24.0
2021    92       16754.0                   8.0
2022   112        8684.0                   5.0
2023   566      225310.0                 194.0
2024  1007       51800.0                  62.0
2025  1660      968462.0                2291.0
2026  1549       81428.0                2652.0
```

### share of each year's videos found by the views-sorted search

```
      share_found_by_views_sort
year                           
2019                       0.85
2020                       0.66
2021                       0.63
2022                       0.65
2023                       0.64
2024                       0.76
2025                       0.74
2026                       0.71
```

### brainrot videos (no game) from 2019: share of videos found and of all views by publish year

```
      videos  share_of_videos_%  share_of_views_%
year                                             
2019      59                0.8               0.9
2020      93                1.3               0.4
2021     145                2.0               0.2
2022     172                2.4               0.4
2023     891               12.5              31.6
2024    1325               18.6              16.5
2025    2251               31.7              43.7
2026    2176               30.6               6.3
```

### views concentration, same videos

```
   videos  total_views  top10_share_%  top1pct_share_%
0    7112  17027056443           10.1             35.2
```

### youtube brainrot videos (no game) by publish month vs reddit brainrot rate, 52 months 2022-06..2026-09 (Spearman; p from circular shifts)

```
                           r_levels  p_levels  r_changes  p_changes  r_yt_3m_before  r_yt_3m_after
reddit            youtube                                                                         
all six           videos       0.39      0.37      -0.02       0.85            0.37           0.17
                  views        0.43      0.07       0.08       0.45            0.49           0.02
memes + teenagers videos       0.07      0.93      -0.13       0.45            0.08          -0.18
                  views        0.33      0.41      -0.08       0.60            0.33           0.05
```

### top months: reddit rate (memes + teenagers, per 10,000 words), youtube views (millions), youtube videos found

```
                                                                                        0
reddit_top5          2023-11 2.30, 2024-04 1.64, 2023-12 1.60, 2025-01 1.45, 2024-07 1.37
youtube_views_top5    2025-05 1752, 2025-06 1232, 2023-07 1039, 2025-07 1002, 2023-08 939
youtube_videos_top5       2026-09 446, 2025-05 284, 2025-09 272, 2025-06 269, 2025-07 260
```
