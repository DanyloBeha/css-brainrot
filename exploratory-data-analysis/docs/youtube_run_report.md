# YouTube collection: run report

Written by `python -m src.yt_run` at the end of every run (`--report` rewrites it without running). Numbers only; no titles. The attempt log starts with the version that added it: earlier pages are in the status table but not in the attempt tables.

## Runs

unusable = YouTube answered but the page has no data (login or age check, unavailable); scraper_errors = the scraper failed (timeout, crash) or was blocked.

```
                                                     started_at  minutes  workers  batch_size  comments        ended_by  pages    ok  unusable  scraper_errors  pages_per_hour
run_id                                                                                                                                                                        
2026-10-05T13:50:07+00:00             2026-10-05T13:50:07+00:00      0.6        2          12        10  target reached     12    12         0               0          1200.0
2026-10-05T13:56:40+00:00 (this run)  2026-10-05T13:56:40+00:00    526.5        2         500        10  target reached   9952  9903        49               0          1134.0
```

## Pages fetched (all videos in the database)

Error rate (pages without data) = 0.5% of 10000 pages.

```
                        videos  share_%
status                                 
CONTENT_CHECK_REQUIRED       1      0.0
ERROR                        5      0.0
LIVE_STREAM_OFFLINE          2      0.0
LOGIN_REQUIRED              42      0.4
OK                        9949     99.5
UNPLAYABLE                   1      0.0
```

## Error types (logged attempts)

9964 attempts logged; not ok = 49 (0.5%); scraper errors = 0 (0.0%).

```
                        pages  median_seconds example  share_of_attempts_%
status                                                                    
CONTENT_CHECK_REQUIRED      1             1.0    None                  0.0
ERROR                       5             0.7    None                  0.1
LIVE_STREAM_OFFLINE         2             1.8    None                  0.0
LOGIN_REQUIRED             40             1.3    None                  0.4
UNPLAYABLE                  1             3.5    None                  0.0
```

Seconds per page (all attempts):

```
       seconds
count   9964.0
mean       6.3
std        2.3
min        0.4
50%        5.7
90%        9.4
99%       14.1
max       21.4
```

## Fields of the 9949 ok pages

Missing = null in the dataset (hidden likes, comments off, comment count not read in time), never filled with 0.

```
                     missing  share_%
published_at             0.0      0.0
view_count               0.0      0.0
like_count             164.0      1.6
comment_count          660.0      6.6
duration_s               0.0      0.0
category                 0.0      0.0
subscribers_approx     217.0      2.2
tags (none given)     3102.0     31.2
comments_off (true)    647.0      6.5
```

## Search quality

shown = videos the query listed; new_unique = not seen in an earlier query; overlap = share already seen; title_match = share of listed videos whose title matches the brainrot lexicon (the rest matched the query in the description, tags or by YouTube's loose matching); ended: cap = the cap was reached, end = YouTube had no more results, stopped = scrolling stalled.

```
   queries  videos_shown  unique_videos  duplicate_share_%  title_match_%_of_unique  ended_at_cap  ran_out_of_results  minutes_of_search
0       55         21817          10081               53.8                     81.7            26                  29               36.1
```

By tier:

```
           queries  shown  new_unique  title_match_%_avg  seconds_per_query
tier                                                                       
ambiguous        2   1000         620                3.1               45.4
core             6   2871        1419               96.5               51.2
core+year       35  12126        4975               90.2               35.2
extended        12   5820        3067               93.6               44.4
```

By sort:

```
       queries  shown  new_unique  title_match_%_avg  seconds_per_query
sort                                                                   
date        27  13163        4283               82.8               45.5
views       28   8654        5798               93.8               33.4
```

Per query:

```
                           tier  results  new_unique  overlap_%  title_match_% ended  seconds
term           sort                                                                          
brainrot       date        core      489         457        6.5           97.8   end     53.0
brain rot      views       core      456         199       56.4           97.6   end     47.2
               date        core      441          11       97.5           97.3   end     47.3
skibidi        views       core      490         489        0.2           93.7   end     57.8
               date        core      500         125       75.0           94.8   cap     50.7
rizz           views   extended      500         500        0.0           95.6   cap     42.9
               date    extended      500          46       90.8           95.0   cap     44.9
gyatt          views   extended      500         500        0.0           97.6   cap     43.4
               date    extended      500         100       80.0           92.0   cap     43.5
fanum tax      views   extended      500         497        0.6           87.6   cap     41.9
               date    extended      500         106       78.8           85.2   cap     43.4
mewing         views   extended      500         500        0.0           93.4   cap     44.0
               date    extended      500          64       87.2           92.4   cap     43.4
tralalero      views   extended      476         405       14.9           97.1   end     47.7
               date    extended      453          15       96.7           96.9   end     46.1
tung tung      views   extended      464         324       30.2           95.9   end     46.6
               date    extended      427          10       97.7           95.1   end     45.1
sigma          views  ambiguous      500         483        3.4            3.6   cap     44.8
               date   ambiguous      500         137       72.6            2.6   cap     46.0
brainrot 2020  views  core+year      197         191        3.0           99.5   end     23.2
               date   core+year      500         301       39.8           89.4   cap     45.4
brainrot 2021  views  core+year       55          45       18.2          100.0   end     11.9
               date   core+year      500         221       55.8           85.6   cap     43.9
brainrot 2022  views  core+year       50          40       20.0           98.0   end     12.1
               date   core+year      500         378       24.4           81.8   cap     44.3
brainrot 2023  views  core+year      109          88       19.3           99.1   end     16.9
               date   core+year      500         240       52.0           77.2   cap     45.7
brainrot 2024  views  core+year      227         191       15.9           99.6   end     26.8
               date   core+year      500         214       57.2           88.8   cap     44.8
brainrot 2025  views  core+year      231         162       29.9           94.4   end     27.6
               date   core+year      500         248       50.4           88.8   cap     44.9
brainrot 2026  views  core+year      346         235       32.1           98.3   end     37.7
               date   core+year      500         117       76.6           86.7   cap     41.3
brain rot 2020 views  core+year      329          55       83.3           99.4   end     35.1
               date   core+year      500          76       84.8           79.8   cap     44.0
brain rot 2021 views  core+year      147          42       71.4           97.3   end     20.1
brain rot 2022 views  core+year      247          94       61.9           98.4   end     28.8
brain rot 2021 date   core+year      500          94       81.2           76.6   cap     45.0
brainrot       views       core      495         138       72.1           97.6   end     51.4
brain rot 2023 views  core+year      345         106       69.3           98.8   end     40.1
brain rot 2022 date   core+year      500         109       78.2           69.0   cap     47.0
brain rot 2024 views  core+year      432         147       66.0           97.9   end     46.0
brain rot 2023 date   core+year      500          40       92.0           79.0   cap     49.3
brain rot 2025 views  core+year      343         124       63.8           96.5   end     38.5
brain rot 2024 date   core+year      500          30       94.0           87.4   cap     45.1
brain rot 2025 date   core+year      378          72       81.0           78.0   end     42.4
brain rot 2026 views  core+year      413          51       87.7           98.1   end     44.9
skibidi 2020   views  core+year      116          75       35.3           96.9   end     16.8
brain rot 2026 date   core+year      475          31       93.5           90.7   end     50.7
skibidi 2021   views  core+year       24          17       29.2           95.8   end     10.7
skibidi 2020   date   core+year      500         378       24.4           74.6   cap     44.8
skibidi 2022   views  core+year       62          44       29.0          100.0   end     13.9
skibidi 2021   date   core+year      500         320       36.0           68.9   cap     41.8
skibidi 2023   views  core+year      100          56       44.0          100.0   end     15.8
skibidi 2022   date   core+year      500         343       31.4           85.3   cap     45.9
```

Failed searches (logged):

```
(none)
```
