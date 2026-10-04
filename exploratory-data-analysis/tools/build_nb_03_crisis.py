import sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from nbhelpers import SETUP, code, fig_cell, md, q, write
ROOT = HERE.parent

M = "figs_crisis"
C = []
C.append(md("""# 03 Crises, negativity and doomscrolling proxies (Phase 4, H4)
Working notebook. Figures C20-C24, C26-C29 (plus C20b). The story is merged into `eda.ipynb` later."""))
C.append(code(SETUP))

C.append(md("""## Design of the H4 analysis
**Question.** Do crises intensify negativity and doomscrolling-like behaviour? Reddit records posting, not reading, so "doomscrolling" can only be proxied (talk about it, and patterns of active posting). Claims stay at community level: no statement about individuals or clinical mood.

**Events inside the data range** (dates checked on 2026-10-04 against news and reference sources): the WHO declares COVID-19 a pandemic (11 March 2020), the full-scale Russian invasion of Ukraine (24 February 2022), the Hamas attack on Israel that starts the Gaza war (7 October 2023), and the assassination of Charlie Kirk (10 September 2025). The last one was not on our first list: it showed up as the busiest r/nosurf day (11 September 2025: 530 comments, 2.8 times the month before; three threads carried 72% of the day, the two biggest about the killing).

**Communities.** Short-form (r/memes + r/teenagers), long-form (r/books + r/explainlikeimfive), baseline (r/todayilearned) and r/nosurf. **No news subreddits are in the data yet** (r/worldnews and r/news were planned), so this is only the half of the design that asks whether non-news communities react; we cannot yet show that news communities react more.

**Statistic.** For each event and community, the change in an outcome between the 8 weeks before the event (days -56 to -1) and the 4 weeks after (days 0 to 27), computed as a ratio of sums over all comments in the window. **Placebo test:** the same statistic at 400 random fake dates (never within 120 days of a real event); `p` is the share of fake dates with an equally large or larger absolute change. We use this instead of a textbook standard error because the data are time-slot samples (about 10-15 slots a month in the big subreddits), so day-to-day values are sparse and autocorrelated.

**Outcomes.** Mean VADER compound score (tone), words about the event itself (to check the event reached the community), crisis words in general, and `doomscroll*` mentions per 10,000 words. VADER is a word list; it has not yet been compared with hand-labeled comments (a 100-comment file is ready for the team in `data/processed/derived/`).

**Not done.** Emotion categories (fear, anger, sadness, planned C25): the NRC lexicon is not available offline. US anxiety/depression indicators from the CDC (planned optional C30). News subreddits (see above)."""))

C.append(q("Q20", "Do crises show up in what people write?",
  "An effect on tone only makes sense if the crisis was part of the conversation.",
  "Monthly rate of a broad list of crisis words (war, pandemic, covid, lockdown, invasion, Ukraine, Gaza, Hamas, Israel, Palestine, genocide, terror, shooting, assassination, crisis, recession, famine, refugees, earthquake, hurricane) per 10,000 words, per subreddit, 3-month mean; the four events are dashed lines. Months with under 50,000 words are dropped.",
  "r/memes shows one clear crisis peak: 34 crisis words per 10,000 words in March 2022, 4.1 times its monthly median (8.2). The other communities have no common peak: r/teenagers peaks in July 2026 (18.2, median 4.2), r/books in December 2025 (12.3, median 5.9), r/todayilearned in August 2022 (18.4, median 11.6), r/nosurf in December 2020 (6.8, median 3.1) and r/explainlikeimfive in October 2012 (14.8, median 5.4).",
  "Only r/memes reacts strongly in the broad measure. Words like war, crisis or shooting appear in games, history, books and jokes all the time, so the broad list is noisy. The event-specific words in Q20b are the cleaner check.",
  "Did each event actually reach each community (Q20b)?"))
C.extend(fig_cell("c20", M))

C.append(q("Q20b", "Did each event reach each community?",
  "If an event leaves no trace in a community's vocabulary, finding no change in tone there says little.",
  "Weekly rate of event-specific words (covid/pandemic/lockdown; Ukraine/Russia/Putin/invasion; Gaza/Hamas/Israel/Palestine; Kirk/Turning Point/assassination) in event time, as change versus the 8 weeks before. The gray band marks the four weeks used in the test. Four community groups, four events.",
  "Event words rose in 13 of 16 community-event pairs (p < 0.05 against random dates). Short-form: +8.2 (COVID), +56.4 (Ukraine), +5.6 (Gaza), +4.1 (Kirk) per 10,000 words. Long-form: +4.6, +2.1, +3.9, +2.0. r/nosurf: +6.3, +5.0, +5.0, +5.2. r/todayilearned reacted to COVID (+4.0) but not to the other three (+0.4, -0.6, +0.3).",
  "All three conversational communities noticed all four events; the Ukraine invasion dominated r/memes and r/teenagers. r/todayilearned, a feed of facts, is the exception, so it is a useful low-exposure comparison. This is the manipulation check for the tests that follow.",
  "Did tone change with the attention (Q21)?"))
C.extend(fig_cell("c20b", M))

C.append(code("""eff = pd.read_parquet(AGG / "event_effects.parquet")
t = eff[eff.outcome == "sentiment"].assign(cell=lambda d: d.effect.map("{:+.3f}".format) + "  (p=" + d.p.map("{:.2f}".format) + ")")
t.pivot(index="group", columns="event", values="cell").loc[["short_form", "long_form", "baseline", "reflective"]]"""))

C.append(q("Q21", "Did tone get more negative after the events? (H4)",
  "H4: crises intensify negativity. The core signal is spillover into communities that are not about news.",
  "Weekly mean VADER compound score in event time (week 0 = days 0-6), as change versus the 8 weeks before, for four community groups and four events (table above gives the 4-week change and the placebo p-value for each pair).",
  "After the three violent events (Ukraine, Gaza, Kirk) tone was lower than before in 11 of the 12 community-event pairs (the twelfth, r/todayilearned after Kirk, is zero), by up to 0.05 compound points. The largest drops are in r/nosurf (Kirk -0.053, Gaza -0.050), r/todayilearned (Ukraine -0.044) and long-form (Ukraine -0.038). After the COVID declaration tone rose slightly in three groups (+0.007 to +0.019) and fell in r/nosurf (-0.037).",
  "The direction is fairly consistent for violent events but the sizes are small: for scale, r/nosurf's mean tone fell by 0.20 over nine years (0.36 in 2017, 0.16 in 2026). The weekly lines are noisy, mostly because each week rests on a few time slots. Whether the dips exceed chance is tested in Q27.",
  "Is the dip larger than a random month would produce (Q27)? And does talk about doomscrolling rise (Q22)?"))
C.extend(fig_cell("c21", M))

C.append(q("Q22", "Did talk about doomscrolling rise after the events?",
  "The doomscrolling half of H4: if crises push people to scroll, they might also talk about it.",
  "Weekly `doomscroll*` and `doom surf*` mentions per 10,000 words in event time, as change versus the 8 weeks before. r/nosurf is the only community that uses the word often (about 1.6 per 10,000 words); the other five are pooled in gray.",
  "Four-week changes in r/nosurf: COVID 0.0 (p = 1.0), Ukraine +0.8 (p = 0.05), Gaza +0.5 (p = 0.16), Kirk -0.3 (p = 0.28), against a placebo spread of about 0.3. The pooled other communities stay near zero.",
  "No clear rise. The Ukraine invasion is the only borderline case, and it is one of four tests. Counting mentions measures talk about doomscrolling, not scrolling; lurking is invisible.",
  "Does the daily rhythm of posting change (Q23)?"))
C.extend(fig_cell("c22", M))

C.append(q("Q23", "Did r/nosurf's daily rhythm change after the events?",
  "Doomscrolling is often described as late-night behaviour; a shift in when people post would be a behavioural trace.",
  "Share of r/nosurf comments by UTC weekday and hour in the 4 weeks after minus the 8 weeks before (percentage points), diverging palette centered on zero, smoothed over 3 hours. r/nosurf only: it is the only community with every comment, so cells are not distorted by sampling. As a yardstick we computed the largest cell difference at 150 random fake dates.",
  "The largest single-cell shifts are 0.56 percentage points (COVID), 0.50 (Ukraine), 0.37 (Gaza) and 0.77 (Kirk). Ninety-five percent of random fake dates produce a largest shift below 0.82, so none of the four events moves the rhythm more than a random date does. The strongest cells for the Kirk event fall on the event day and the day after, when the busiest r/nosurf day (11 September 2025) happened.",
  "No evidence of a changed daily rhythm; the post window of four weeks holds only about 3,000-6,000 comments, so cells are noisy and only large shifts could show.",
  "Do posting sessions get longer (Q24)?"))
C.extend(fig_cell("c23", M))

C.append(q("Q24", "Did posting sessions in r/nosurf get longer?",
  "Longer unbroken stretches of activity are the closest thing to a scrolling session that posting data can show.",
  "Gap-based sessions (messages by one author with gaps of at most 30 minutes) from comments and submissions, r/nosurf only; empirical cumulative distribution of the length of sessions with 2 or more messages, 8 weeks before versus 4 weeks after.",
  "The share of sessions with two or more messages is 11.5% vs 11.4% (COVID), 13.9% vs 11.9% (Ukraine), 12.5% vs 13.3% (Gaza) and 17.0% vs 16.0% (Kirk). Their median length is 6 vs 6 minutes, 6 vs 9, 6 vs 7 and 6 vs 6.",
  "No change. This only sees active posting; reading without posting is invisible, so a real change in scrolling time could not show here.",
  "Do the same people change (Q26)?"))
C.extend(fig_cell("c24", M))

C.append(q("Q26", "Do the same r/nosurf authors write differently after an event?",
  "A change in average tone could come from different people posting; following the same authors removes that.",
  "Authors with comments in both windows (8 weeks before, 4 weeks after): mean change in their VADER score, 95% bootstrap interval over authors, and the 95% range of the same statistic at 120 random fake dates (gray band).",
  "The same authors wrote less positively after all four events: -0.037 (COVID, 322 authors), -0.042 (Ukraine, 401), -0.058 (Gaza, 385), -0.070 (Kirk, 613). The intervals of Gaza and Kirk exclude zero; only the Kirk change lies outside the random-date band (-0.063 to +0.058).",
  "A consistent small negative shift among people who keep posting, in the one community where we see everyone. But random dates also produce shifts of this size, and the topic of the week (people discussing the news in their own words) changes the vocabulary VADER reads, so this is tone of the text, not mood of the people.",
  "Is the whole pattern distinguishable from chance (Q27)?"))
C.extend(fig_cell("c26", M))

C.append(q("Q27", "Is the dip real? (placebo test)",
  "A dip means little unless random dates show nothing like it.",
  "For short-form and r/nosurf: histogram of the change in mean tone at 400 random fake dates (gray) with the real event as a colored line and its p-value. Across all four groups and four events (16 tests) we count the p-values below 0.05.",
  "Three of 16 tests fall outside the random range: r/nosurf after Gaza (p = 0.04) and after Kirk (p = 0.03), and r/todayilearned after Ukraine (p = 0.04). Short-form p-values are 0.44, 0.15, 0.71 and 0.32. By chance 0.8 of 16 would be expected.",
  "Weak, not nothing: if the 16 tests were independent, three or more significant would happen about 4% of the time by chance. They are not independent (the same weeks and communities recur), and we ran many tests, so we do not call it a finding. What we can say: any effect of these events on tone is small and, for most communities, indistinguishable from the weekly noise.",
  "Is uncertainty in the world, as a continuous measure, related to tone (Q28)?"))
C.extend(fig_cell("c27", M))

C.append(q("Q28", "Does world uncertainty lead or follow tone and crisis talk?",
  "Four events are few; a continuous crisis-intensity series uses all 160 months.",
  "Cross-correlation, at lags of -6 to +6 months, between monthly changes in the World Uncertainty Index (global, GDP-weighted; Ahir, Bloom and Furceri) and monthly changes in mean tone or crisis-word rate, per community group (2013-2026). Both series are first-differenced so that shared long-run trends do not create correlation. Gray band = approximate 95% range for no relation.",
  "Nothing reliable: the largest absolute correlation is 0.19 against a noise band of +/-0.15, and the same-month correlation between uncertainty and crisis words is between -0.09 and +0.08 in all groups.",
  "Monthly changes in global uncertainty are unrelated to changes in tone or crisis wording in these communities. The index is global and dominated by large economies, and our crisis words are broad, so a null here does not rule out reactions to specific events.",
  "Did tone shift at other moments (Q29)?"))
C.extend(fig_cell("c28", M))

C.append(q("Q29", "When did tone shift, and does it line up with the events?",
  "A model-free check: find the breaks in each community's tone and see whether the four events are near them.",
  "Change-point detection (PELT, least-squares cost, penalty from the noise of month-to-month differences) on the monthly mean VADER score of each subreddit; breaks drawn as dotted lines, events as dashed lines, step lines show the mean between breaks.",
  "17 change-points in total (r/teenagers 6, r/nosurf 4, r/books 3, r/explainlikeimfive 2, r/memes 1, r/todayilearned 1). One falls within three months of an event: r/nosurf in December 2023, two months after the Hamas attack. Chance alone would put about 3 there.",
  "Tone shifts in these communities follow slow changes (new users, moderation, platform changes), not the crisis dates. This is consistent with Q27 and with the long drift of tone in r/nosurf (mean score 0.36 in 2017, 0.16 in 2026): the drift over many years is much larger than any event effect we can detect.",
  "What would settle H4? News subreddits as a contrast group and a hand-checked sentiment measure."))
C.extend(fig_cell("c29", M))

C.append(md("""## What H4 shows
- **Events reach the communities.** Event words rose in 13 of 16 community-event pairs; r/todayilearned is the exception (Q20b).
- **Tone: small, consistent direction, weak evidence.** Tone was lower after the three violent events in 11 of 12 pairs, by at most 0.05; three of 16 tests are outside the placebo range, about what we would expect by chance given many correlated tests (Q21, Q27). The same r/nosurf authors wrote 0.04-0.07 less positively afterwards, only Kirk beyond random dates (Q26).
- **Doomscrolling proxies: nothing.** Talk about doomscrolling, daily rhythm and session length of r/nosurf did not change beyond random variation (Q22-Q24).
- **No link to a continuous uncertainty index** and no change-points at the event dates (Q28, Q29).
- **Not yet tested:** the news-subreddit contrast, which is the cleanest way to separate "the crisis" from general drift; hand-validated sentiment."""))

write(C, str(ROOT / "notebooks" / "03_crisis_h4.ipynb"))
print("written")
