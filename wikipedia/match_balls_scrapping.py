# %%
import requests
import pandas as pd
import json
from io import StringIO
import numpy as np


# %%
PAGE_TITLE = "List_of_FIFA_World_Cup_official_match_balls"
API_URL = "https://en.wikipedia.org/w/api.php"

# %%
def get_page_html(title: str) -> str:
    """Pide a la MediaWiki API el HTML ya renderizado del artículo."""
    params = {
        "action": "parse",
        "page": title,
        "format": "json",
        "prop": "text",
    }
    resp = requests.get(API_URL, params=params, headers={
        "User-Agent": "WorldCupAnalyticsAgent/1.0 (portfolio project)"
    })
    resp.raise_for_status()
    data = resp.json()
    return data["parse"]["text"]["*"]


def extract_tables(html: str) -> list[pd.DataFrame]:
    """pandas.read_html parsea todas las <table> del HTML."""
    return pd.read_html(html)


# %%
html = get_page_html(PAGE_TITLE)

# %%
tables = pd.read_html(StringIO(html))

# %%
match_balls_df = tables[0].copy()
match_balls_df = match_balls_df[~match_balls_df['Edition'].str.contains('women')].reset_index(drop=True).copy()

# %%
match_balls_df.rename(columns={
    'Edition': 'tournament_id',
    'Match ball': 'ball_name',
    'Manufacturer': 'manufacturer'}, inplace=True)

match_balls_df['tournament_id'] = 'WC-' + match_balls_df['tournament_id']
match_balls_df.drop(columns=['Match ball.1', 'Panels',	'Additional information', 'Ref.'], inplace=True)

match_balls_df = match_balls_df.iloc[1:].reset_index(drop=True)

tiento = {
    'tournament_id': 'WC-1930',
    'ball_name': 'Tiento',
    'manufacturer': np.nan
}
t_model = {
    'tournament_id': 'WC-1930',
    'ball_name': 'T-Model',
    'manufacturer': np.nan
}

match_balls_df = pd.concat([match_balls_df, pd.DataFrame([tiento, t_model])], ignore_index=True)

# %%
# order by tournament_id
match_balls_df = match_balls_df.sort_values(by='tournament_id').reset_index(drop=True)
match_balls_df['ball_id'] = match_balls_df.index + 1

# %%
match_balls_df.loc[match_balls_df['tournament_id'] == 'WC-1994', 'ball_name'] = 'Questra'
match_balls_df['manufacturer'] = match_balls_df['manufacturer'].str.split(',').str[0]

# %%
match_balls_df.to_csv("data/processed/match_balls.csv", index=False)