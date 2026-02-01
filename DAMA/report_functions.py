import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from IPython.display import display


# --------------------------------------------------------
# Data Ingestion
# --------------------------------------------------------

def load_tiered_data(data_dir='../data', decks_meta_path='../data/decks_metadata/en_US.json'):
    """
    Loads Casual, Advanced, and Competitive datasets into a single structure.
    """
    tiers = ['casual', 'advanced', 'competitive']
    tiered_data = {}

    # Load Deck Names
    try:
        with open(decks_meta_path, 'r') as f:
            deck_meta = json.load(f)
    except:
        deck_meta = {}

    def get_deck_name(deck_id):
        # Handle string/int conversion safely
        return deck_meta.get(str(deck_id), {}).get('name', f"Deck {deck_id}")

    # Load each tier file
    for t in tiers:
        fname = f"meta_stats_{t}.json"
        path = os.path.join(data_dir, fname)
        # Handle absolute/relative paths
        if not os.path.exists(path):
            # Try looking relative to the script location if typical path fails
            script_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(script_dir, "..", "data", fname)

        if os.path.exists(path):
            with open(path, 'r') as f:
                tiered_data[t.capitalize()] = json.load(f)
        else:
            print(f"Warning: {fname} not found.")

    return {
        'tiers': tiered_data,
        'deck_names_func': get_deck_name
    }


# --------------------------------------------------------
# Logic Helpers (Calculations)
# --------------------------------------------------------

def get_expected_winrate(c_class, level):
    """Defines baseline expected winrate per level/class."""
    if c_class == 'Heavy': return 0.46 + (level * 0.03)  # Aggro
    if c_class == 'Light': return 0.34 + (level * 0.06)  # Control
    return 0.40 + (level * 0.04)  # Midrange


def prepare_card_df(data_fragment):
    """
    Converts a data dictionary (containing 'card_stats') into a DataFrame.
    """
    rows = []
    stats_dict = data_fragment.get('card_stats', {})

    for name, stats in stats_dict.items():
        plays = stats.get('plays', 0)
        wins = stats.get('wins', 0)
        wr = wins / plays if plays > 0 else 0

        level = stats.get('level', 1)
        c_class = stats.get('class', 'Medium')

        expected_wr = get_expected_winrate(c_class, level)
        efficiency = wr - expected_wr if plays >= 5 else 0
        avg_turn = stats.get('turn_sum', 0) / plays if plays > 0 else 0

        rows.append({
            'Name': name,
            'Class': c_class,
            'Type': stats.get('type', 'Unknown'),
            'Level': level,
            'Plays': plays,
            'Wins': wins,
            'WinRate': wr,
            'Efficiency': efficiency,
            'AvgTurn': avg_turn
        })

    return pd.DataFrame(rows)


def calculate_fun_scores(data_fragment):
    """
    Calculates Fun Scores. Requires 'deck_stats' and 'deck_names_func'.
    """
    rows = []
    deck_stats = data_fragment.get('deck_stats', {})
    get_name = data_fragment.get('deck_names_func', lambda x: str(x))

    for deck_id, stats in deck_stats.items():
        plays = stats.get('plays', 0)
        if plays == 0: continue

        avg_swing = stats.get('swinginess', 0.0) / plays
        avg_inter = stats.get('interactivity', 0) / plays
        comeback_rate = stats.get('comebacks', 0) / plays

        # Weighted Score (0-100)
        # Swinginess target: ~10% per turn is exciting
        # Interactivity target: ~5 actions per game
        # Comeback target: ~30%
        score = (min(1.0, avg_swing / 0.10) * 20 +
                 min(1.0, avg_inter / 5.0) * 40 +
                 min(1.0, comeback_rate / 0.3) * 40)

        rows.append({
            'Deck': get_name(deck_id),
            'Swinginess': avg_swing,
            'Interactivity': avg_inter,
            'ComebackRate': comeback_rate,
            'FunScore': score
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------
# Visualization Functions (Tier-Aware)
# --------------------------------------------------------

def plot_skill_scalability(report_data):
    """
    Compares Winrates between Casual and Competitive tiers.
    """
    tiers = report_data['tiers']
    if 'Casual' not in tiers or 'Competitive' not in tiers:
        print("Need both Casual and Competitive data for Skill Analysis.")
        return

    # Helper to get quick DF
    def get_tier_df(tier_name):
        return prepare_card_df({'card_stats': tiers[tier_name]['card_stats']})

    df_casual = get_tier_df('Casual')
    df_comp = get_tier_df('Competitive')

    # Filter low plays
    df_casual = df_casual[df_casual['Plays'] >= 5]
    df_comp = df_comp[df_comp['Plays'] >= 5]

    # Merge
    merged = pd.merge(df_casual[['Name', 'WinRate']], df_comp[['Name', 'WinRate']],
                      on='Name', suffixes=('_Cas', '_Comp'))

    merged['Skill_Delta'] = merged['WinRate_Comp'] - merged['WinRate_Cas']
    merged = merged.sort_values('Skill_Delta', ascending=False)

    fig = go.Figure()

    for i, row in merged.iterrows():
        color = 'green' if row['Skill_Delta'] > 0 else 'red'
        # Draw Arrow/Line
        fig.add_trace(go.Scatter(
            x=[row['WinRate_Cas'], row['WinRate_Comp']],
            y=[row['Name'], row['Name']],
            mode='lines+markers',
            line=dict(color=color, width=2),
            marker=dict(symbol=['circle', 'arrow-right'], size=[8, 12]),
            name=row['Name'],
            showlegend=False,
            hovertemplate=f"Casual: {row['WinRate_Cas']:.1%}<br>Comp: {row['WinRate_Comp']:.1%}<br>Delta: {row['Skill_Delta']:+.1%}"
        ))

    fig.update_layout(
        title="Skill Expression: Casual (Left) vs Competitive (Right) Winrate",
        xaxis_title="Winrate",
        height=max(400, len(merged) * 30),
        xaxis=dict(tickformat='.0%', range=[0, 1]),
        template='plotly_white'
    )
    fig.add_vline(x=0.5, line_dash="dash", line_color="gray")
    fig.show()


def plot_deck_performance(report_data, target_tier='Competitive'):
    if target_tier not in report_data['tiers']: return
    data = report_data['tiers'][target_tier]

    deck_rows = []
    for did, stats in data['deck_stats'].items():
        plays = stats['plays']
        wr = stats['wins'] / plays if plays > 0 else 0
        deck_rows.append({
            'Deck Name': report_data['deck_names_func'](did),
            'WinRate': wr
        })

    deck_df = pd.DataFrame(deck_rows).sort_values('WinRate', ascending=False)
    fig = px.bar(deck_df, x='Deck Name', y='WinRate', color='WinRate',
                 title=f'Overall Deck Performance ({target_tier})',
                 color_continuous_scale='RdYlGn', range_color=[0.3, 0.7])
    fig.add_hline(y=0.5, line_dash="dash", line_color="black")
    fig.update_layout(yaxis_tickformat='.0%', template='plotly_white')
    fig.show()


def plot_matchup_matrix(report_data, target_tier='Competitive'):
    if target_tier not in report_data['tiers']: return
    data = report_data['tiers'][target_tier]

    all_decks = sorted(list(data['deck_stats'].keys()), key=int)
    matrix_data = []
    labels = [report_data['deck_names_func'](d) for d in all_decks]

    for d1 in all_decks:
        row = []
        for d2 in all_decks:
            key = f"{d1}_vs_{d2}"
            stats = data['matchup_stats'].get(key, {'wins': 0, 'plays': 0})
            wr = stats['wins'] / stats['plays'] if stats['plays'] > 0 else 0.5
            row.append(wr)
        matrix_data.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=matrix_data, x=labels, y=labels,
        colorscale='RdBu', zmin=0.2, zmax=0.8
    ))
    fig.update_layout(title=f'Matchup Matrix ({target_tier})', template='plotly_white')
    fig.show()


def plot_card_efficiency(report_data, target_tier='Competitive'):
    if target_tier not in report_data['tiers']: return
    tier_data = report_data['tiers'][target_tier]

    df = prepare_card_df({'card_stats': tier_data['card_stats']})
    import numpy as np
    df['Level_Jitter'] = df['Level'] + np.random.uniform(-0.15, 0.15, size=len(df))

    fig = px.scatter(df, x='Level_Jitter', y='WinRate', color='Class',
                     size='Plays', hover_name='Name',
                     title=f'Card Efficiency vs Target ({target_tier})',
                     color_discrete_map={'Heavy': 'red', 'Medium': 'green', 'Light': 'blue'})

    x_range = np.linspace(1, 10, 50)
    for cls, color in [('Heavy', 'red'), ('Medium', 'green'), ('Light', 'blue')]:
        fig.add_trace(go.Scatter(x=x_range, y=[get_expected_winrate(cls, x) for x in x_range],
                                 mode='lines', name=f'{cls} Target', line=dict(color=color, dash='dot')))
    fig.update_layout(xaxis=dict(tickmode='linear', dtick=1), template='plotly_white')
    fig.show()


def plot_fun_analysis(report_data, target_tier='Competitive'):
    if target_tier not in report_data['tiers']: return
    tier_data = report_data['tiers'][target_tier]

    df = calculate_fun_scores({
        'deck_stats': tier_data['deck_stats'],
        'deck_names_func': report_data['deck_names_func']
    })

    if df.empty: return
    fig = px.bar(df, x='Deck', y='FunScore', color='FunScore',
                 title=f"Engagement Analysis ({target_tier})",
                 labels={'FunScore': 'Fun Score (0-100)'},
                 hover_data=['Swinginess', 'Interactivity', 'ComebackRate'])
    fig.show()


def plot_matchup_duration(report_data, target_tier='Competitive'):
    if target_tier not in report_data['tiers']: return
    data = report_data['tiers'][target_tier]
    rows = []

    for key, stats in data.get('matchup_stats', {}).items():
        if stats['plays'] == 0: continue
        avg_round = (stats['total_turns'] / stats['plays']) / 2
        d1, d2 = key.split('_vs_')
        name = f"{report_data['deck_names_func'](d1)} vs {report_data['deck_names_func'](d2)}"
        rows.append({'Matchup': name, 'Avg Round': avg_round})

    df = pd.DataFrame(rows).sort_values('Avg Round')
    if df.empty: return

    fig = px.bar(df, x='Avg Round', y='Matchup', orientation='h', color='Avg Round',
                 title=f'Match Duration ({target_tier})', color_continuous_scale='Viridis')
    fig.add_vline(x=5, line_dash="dot", line_color="red", annotation_text="Aggro")
    fig.add_vline(x=10, line_dash="dot", line_color="blue", annotation_text="Control")
    fig.update_layout(template='plotly_white', xaxis_range=[0, 20])
    fig.show()


# --------------------------------------------------------
# Tables and AI
# --------------------------------------------------------

def display_top_cards(report_data, target_tier='Competitive', limit=10):
    if target_tier not in report_data['tiers']: return
    df = prepare_card_df({'card_stats': report_data['tiers'][target_tier]['card_stats']})
    df = df.sort_values('Efficiency', ascending=False)
    print(f"### Top Cards ({target_tier})")
    display(df[['Name', 'Level', 'WinRate', 'Efficiency']].head(limit).style.format({
        'WinRate': '{:.2%}', 'Efficiency': '{:+.2%}'
    }))


def display_underperforming_cards(report_data, target_tier='Competitive', min_plays=10, limit=10):
    if target_tier not in report_data['tiers']: return
    df = prepare_card_df({'card_stats': report_data['tiers'][target_tier]['card_stats']})
    df = df[df['Plays'] >= min_plays].sort_values('Efficiency', ascending=True)
    print(f"### Weakest Cards ({target_tier})")
    display(df[['Name', 'Level', 'WinRate', 'Efficiency']].head(limit).style.format({
        'WinRate': '{:.2%}', 'Efficiency': '{:+.2%}'
    }))


def display_searchable_table(report_data):
    """
    Renders a Master Audit Table containing data from ALL tiers side-by-side.
    """
    tiers_order = ['Casual', 'Advanced', 'Competitive']
    available_tiers = [t for t in tiers_order if t in report_data['tiers']]

    if not available_tiers:
        print("No tier data available.")
        return

    # Build a Base DataFrame with Metadata (Name, Level, Type)
    # We combine all cards found in any tier
    all_cards = {}

    for t in available_tiers:
        raw_df = prepare_card_df({'card_stats': report_data['tiers'][t]['card_stats']})
        for _, row in raw_df.iterrows():
            if row['Name'] not in all_cards:
                all_cards[row['Name']] = {
                    'Name': row['Name'],
                    'Level': row['Level'],
                    'Type': row['Type'],
                    'Class': row['Class']
                }
            # Update/Overwrite metrics for specific tiers
            # We store raw numbers first, format later
            all_cards[row['Name']][f'{t}_WR'] = row['WinRate']
            all_cards[row['Name']][f'{t}_Eff'] = row['Efficiency']
            all_cards[row['Name']][f'{t}_Plays'] = row['Plays']

    # Convert to DataFrame
    df = pd.DataFrame(list(all_cards.values()))

    # Fill NaNs (cards not played in certain tiers)
    df = df.fillna(0)

    # Format Columns for Display
    # We create a list of columns to show.
    # Logic: Metadata -> Casual Stats -> Advanced Stats -> Competitive Stats

    final_cols = ['Name', 'Level', 'Type']
    headers = ['<b>Card Name</b>', '<b>Lvl</b>', '<b>Type</b>']
    cell_values = [df['Name'], df['Level'], df['Type']]

    # Dynamic Color Logic lists
    fill_color = ['lavender'] * 3  # Metadata columns are standard color

    for t in available_tiers:
        # Create formatted strings
        wr_col = f'{t}_WR'
        eff_col = f'{t}_Eff'
        plays_col = f'{t}_Plays'

        # Abbreviate header
        short_t = t[:3]  # "Cas", "Adv", "Com"

        # Format: "55% (+2%)"
        # We only show stats if Plays >= 5, else "-"
        formatted_stats = []
        colors = []

        for index, row in df.iterrows():
            if row[plays_col] < 5:
                formatted_stats.append("-")
                colors.append('#f0f0f0')  # Grey for no data
            else:
                eff_val = row[eff_col]
                text = f"{row[wr_col]:.1%} ({eff_val:+.1%})"
                formatted_stats.append(text)

                # Colorize based on Efficiency
                if eff_val > 0.10:
                    colors.append('#d4edda')  # Green (Strong)
                elif eff_val < -0.10:
                    colors.append('#f8d7da')  # Red (Weak)
                else:
                    colors.append('white')

        headers.append(f'<b>{short_t} WR (Eff)</b>')
        cell_values.append(formatted_stats)
        fill_color.append(colors)

    # Render Plotly Table
    fig = go.Figure(data=[go.Table(
        columnorder=list(range(len(headers))),
        columnwidth=[120, 40, 60] + [80] * len(available_tiers),  # Metadata wider
        header=dict(
            values=headers,
            fill_color='paleturquoise',
            align='left',
            font=dict(color='black', size=12)
        ),
        cells=dict(
            values=cell_values,
            fill_color=fill_color,  # Dynamic coloring
            align='left',
            font=dict(color='black', size=11)
        ))
    ])

    fig.update_layout(
        title="Master Balance Audit (All Tiers)",
        margin=dict(l=10, r=10, t=40, b=10),
        height=max(400, len(df) * 30)
    )
    fig.show()

def get_ai_summary(report_data, api_key):
    """
    Generates a Comprehensive 'Patch Note' style report using Gemini.
    Aggregates data across all tiers to find subtle balance issues.
    """
    try:
        from google import genai
    except ImportError:
        return "Error: `google-genai` package not installed."

    if not api_key or "API_KEY" in api_key:
        return "Error: Invalid API Key."

    # --- CONSTRUCT THE MASTER DATASET ---
    # We need a dataframe that has [Name, Casual_Eff, Comp_Eff, Plays]

    tiers = report_data['tiers']
    # Fallback if tiers are missing
    if 'Casual' not in tiers or 'Competitive' not in tiers:
        return "Error: Simulation must include 'Casual' and 'Competitive' tiers for full analysis."

    def get_tier_stats(tier_name):
        df = prepare_card_df({'card_stats': tiers[tier_name]['card_stats']})
        # Index by name for easy lookup
        return df.set_index('Name')[['WinRate', 'Efficiency', 'Plays', 'Level', 'Type']]

    casual_df = get_tier_stats('Casual')
    adv_df = get_tier_stats('Advanced')  # Optional, but good context
    comp_df = get_tier_stats('Competitive')

    # Get list of all cards played across all tiers
    all_cards = set(casual_df.index).union(comp_df.index)

    card_report_lines = []

    for card in all_cards:
        # Get Stats (Default to 0 if not played in that tier)
        c_eff = casual_df.loc[card, 'Efficiency'] if card in casual_df.index else 0
        c_wr = casual_df.loc[card, 'WinRate'] if card in casual_df.index else 0

        comp_eff = comp_df.loc[card, 'Efficiency'] if card in comp_df.index else 0
        comp_wr = comp_df.loc[card, 'WinRate'] if card in comp_df.index else 0
        comp_plays = comp_df.loc[card, 'Plays'] if card in comp_df.index else 0

        # Metadata (Get from wherever available)
        level = casual_df.loc[card, 'Level'] if card in casual_df.index else (
            comp_df.loc[card, 'Level'] if card in comp_df.index else 0)
        c_type = casual_df.loc[card, 'Type'] if card in casual_df.index else "Unknown"

        # Filters to reduce noise (Must be played at least 5 times in at least one tier)
        if comp_plays < 5 and (casual_df.loc[card, 'Plays'] if card in casual_df.index else 0) < 5:
            continue

        skill_delta = comp_wr - c_wr

        line = f"| {card:<20} | Lvl {level} {c_type:<8} | Cas WR: {c_eff:+.1%} | Comp WR: {comp_eff:+.1%} | Delta: {skill_delta:+.1%} |"
        card_report_lines.append(line)

    # Deck Fun Stats Summary
    fun_summary = ""
    for t in ['Casual', 'Competitive']:
        if t in tiers:
            fun_df = calculate_fun_scores({
                'deck_stats': tiers[t]['deck_stats'],
                'deck_names_func': report_data['deck_names_func']
            })
            avg = fun_df['FunScore'].mean() if not fun_df.empty else 0
            fun_summary += f"- {t} Meta Fun Score: {avg:.1f}/100\n"

    # Game Rules
    rules = ""

    fname = f"rules.md"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "..", "docs", fname)

    if os.path.exists(path):
        with open(path, 'r') as f:
            rules = f.read()

    # --- PROMPT ---

    data_block = "\n".join(sorted(card_report_lines))

    prompt = f"""
    You are the Lead Balance Designer for 'Dust Access', an Expandable Card Game with deckbuilding. 
    We are doing automatic playtests of the structure decks using MCTS AI bots, and you are writing a bullet point list of things that the other Game Designers should change to fix the game's balance.

    GAME RULES:
    {rules}

    OBJECTIVE:
    Analyze the provided Tiered Simulation Data to identify critical balance issues.
    The data compares "Casual" (Low Skill simulation) vs "Competitive" (High Skill simulation).
    Values shown are **Efficiency** (Winrate relative to expected baseline).
    +5% is Very Strong. +10% is Broken. -5% is Weak. -10% is Useless.

    DATA TABLE:
    {data_block}

    ENGAGEMENT METRICS:
    {fun_summary}

    INSTRUCTIONS:
    Write a report as a simple bullet point list. It should contain short phrases which will contain the following informations:

    *   Is the game fun? (Comment on Fun Scores).
    *   Is the skill gap healthy? (Are there cards that reward Competitive play?).
    *   Identify the **UNIVERSAL THREATS** (High efficiency in BOTH Casual and Competitive). These need nerfs.
    *   Identify **NOOB STOMPERS** (High efficiency in Casual, Normal/Low in Competitive). Decide if they are problematic or just part of the learning curve.
    *   **Action:** Propose specific nerfs (e.g., "Increase Cost", "Reduce Damage").
    *   Identify cards that are negative efficiency across the board.
    *   **Action:** Propose buffs to make them viable.
    *   For your suggested changes, explicitly state how they will affect the Casual Meta vs the Competitive Meta.
    *   *Example:* "Nerfing 'Big Club' will save Casual players from frustration but might lower the winrate of Aggro decks in Competitive by 2%."

    Make your tone professional, insightful, and decisive.
    """

    # --- EXECUTION ---
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-3-flash-preview',  # Use the smartest model available
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"## AI Generation Error\nCould not generate report: {str(e)}"


def gemini_api_key(filename=".gemini_api"):
    """
       Reads the Gemini API Key from a local file.
       Searches in the current directory and the parent directory (Project Root).
       """
    search_paths = [
        os.getcwd(),  # Current dir (e.g., /notebooks)
        os.path.dirname(os.getcwd())  # Parent dir (e.g., /ProjectRoot)
    ]

    for path in search_paths:
        filepath = os.path.join(path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as filename:
                    key = filename.read().strip()
                    # Basic validation: API keys usually start with 'AIza'
                    if key.startswith("AIza"):
                        return key
                    else:
                        print(
                            f"Warning: Key in {filename} doesn't look like a valid Gemini Key (should start with AIza).")
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    print(f"Error: '{filename}' not found. Please create this file in your project root with your API key inside.")
    return None