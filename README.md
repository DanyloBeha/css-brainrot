# Brainrot
Effects of doomscrolling and short-form media on discourse, attention, and wellbeing.  
Course: Computational Social Science (CSS) - NaUKMA, 2026  

## Team
1. Danylo Beha - d.beha@ukma.edu.ua
2. Krutkevych Ivan - i.krutkevych@ukma.edu.ua
3. Daria Zasko - d.zasko@ukma.edu.ua

## Structure
```
css-brainrot/
├── dataset-collection/                  # HW 2
│   ├── arctic_download.py               # used for downloading the reddit dataset
│   └── ...
│
├── exploratory-data-analysis/           # HW 3
│   ├── eda.ipynb                        # team notebook (the H4 section holds its own chart code)
│   ├── src/                             # data logic: cleaning, aggregates, text metrics, events (H4 statistics)
│   ├── data/                            # raw and processed data stay local; aggregates/ is tracked
│   ├── fonts/  outputs/  docs/          # Jost fonts for the charts, deliverables, research log
│   └── run_pipeline.py                  # rebuilds every table (docs/pipeline.md); every script is explained in docs/code_guide.md, the H4 charts in docs/figure_index.md
│
├── .gitignore
├── LICENSE
└── README.md
```

## Research overview
### Topic
Analysis of impact of doomscrolling and brainrot on people, their wellbeing and cognitive abilities over time

### Hypotheses and criteria
H1: Discourse is getting shorter and simpler
	- Lexical & NLP approach
	- Temporal & Behavioural aspect
H2: Short-form platforms accelerated this
H3: Wellbeing is getting worse among doomscrollers
H4: Crises intensify doomscrolling and negativity

### Datasets
#### H1
1. Short-form: r/memes, r/teenagers
2. Long-form: r/books, r/explainlikeimfive
3. Baseline: r/AskReddit
4. Qualitative: r/nosurf

#### H2: 
1. [Reels/Shorts Consumption vs Attention Span](https://www.kaggle.com/datasets/jayjoshi37/reelsshorts-consumption-vs-attention-span)

#### H3:
1. [Social Media Addiction dataset](https://www.kaggle.com/datasets/engieid/social-media-addiction-dataset)
2. [The Dark At The End Of The Tunnel: Doomscrolling On Social Media Newsfeeds](https://osf.io/u9f6h/)
3. [Sleep & Doomscrolling Habits Dataset](https://www.kaggle.com/datasets/harpartapsingh13/sleep-and-doomscrolling-habits-dataset)
4. [Social Media and Mental Health](https://www.kaggle.com/datasets/souvikahmed071/social-media-and-mental-health)
5. [Student Social Media & Mental Health](https://www.kaggle.com/datasets/shivasingh4945/student-social-media-and-mental-health-impact)