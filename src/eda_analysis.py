"""
eda_analysis.py
---------------
Generates publication-quality visualizations and exploratory analysis
for the India COVID-19 dataset.
Outputs high-resolution charts saved to the figures/ folder:
  1. daily_trends_india.png: Daily new cases, recoveries, and 7-day rolling average.
  2. top10_confirmed_states.png: Top 10 most impacted states by confirmed cases.
  3. active_vs_recovered_comparison.png: Active vs Recovered breakdown in top states.
  4. recovery_mortality_rates.png: State-wise recovery vs mortality rate comparison.
  5. national_case_distribution.png: Donut chart of Active, Recovered, and Deceased.
  6. correlation_heatmap.png: Correlation matrix across epidemiological indicators.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def set_plot_style():
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#cccccc'
    plt.rcParams['axes.linewidth'] = 0.8
    plt.rcParams['figure.autolayout'] = True

def generate_eda(data_path: str, figures_dir: str):
    os.makedirs(figures_dir, exist_ok=True)
    set_plot_style()

    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Aggregate daily national totals
    national_daily = df.groupby('Date').agg({
        'Confirmed': 'sum',
        'Active': 'sum',
        'Cured': 'sum',
        'Deaths': 'sum',
        'New_Cases': 'sum',
        'New_Deaths': 'sum',
        'New_Recovered': 'sum'
    }).reset_index()

    national_daily['New_Cases_7d_MA'] = national_daily['New_Cases'].rolling(7, min_periods=1).mean()
    national_daily['New_Recovered_7d_MA'] = national_daily['New_Recovered'].rolling(7, min_periods=1).mean()

    # Latest state summary
    latest_date = df['Date'].max()
    latest_states = df[df['Date'] == latest_date].copy().sort_values(by='Confirmed', ascending=False)

    print(f"Generating charts using data up to {latest_date.strftime('%Y-%m-%d')}...")

    # =========================================================================
    # 1. Daily Trends in India (New Cases, Recoveries & 7-Day Moving Average)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    ax.bar(national_daily['Date'], national_daily['New_Cases'], color='#4a90e2', alpha=0.4, label='Daily New Cases', width=1.0)
    ax.plot(national_daily['Date'], national_daily['New_Cases_7d_MA'], color='#1f77b4', linewidth=2.5, label='7-Day MA (New Cases)')
    ax.plot(national_daily['Date'], national_daily['New_Recovered_7d_MA'], color='#2ca02c', linewidth=2.5, linestyle='--', label='7-Day MA (Recovered)')
    
    ax.set_title("COVID-19 Daily Infection & Recovery Trends in India (2020)", fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel("Date", fontsize=12, labelpad=10)
    ax.set_ylabel("Daily Count", fontsize=12, labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{int(x):,}"))
    ax.legend(frameon=True, facecolor='white', loc='upper left')
    plt.xticks(rotation=30)
    p1 = os.path.join(figures_dir, 'daily_trends_india.png')
    plt.savefig(p1, bbox_inches='tight')
    plt.close()
    print(f"Saved: {p1}")

    # =========================================================================
    # 2. Top 10 Most Impacted States (Total Confirmed Cases)
    # =========================================================================
    top10 = latest_states.head(10).sort_values(by='Confirmed', ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    bars = ax.barh(top10['State'], top10['Confirmed'], color='#e74c3c', alpha=0.85, edgecolor='black', linewidth=0.5)
    
    # Annotate bar values
    for bar in bars:
        w = bar.get_width()
        ax.annotate(f" {w:,.0f}", (w, bar.get_y() + bar.get_height() / 2),
                    va='center', ha='left', fontsize=9, fontweight='semibold')

    ax.set_title("Top 10 States by Total Confirmed COVID-19 Cases", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Total Confirmed Cases", fontsize=11, labelpad=10)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{int(x):,}"))
    ax.set_xlim(0, top10['Confirmed'].max() * 1.15)
    p2 = os.path.join(figures_dir, 'top10_confirmed_states.png')
    plt.savefig(p2, bbox_inches='tight')
    plt.close()
    print(f"Saved: {p2}")

    # =========================================================================
    # 3. Stacked Breakdown for Top 10 States: Active, Cured, Deaths
    # =========================================================================
    top10_desc = latest_states.head(10).copy()
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    
    x = np.arange(len(top10_desc))
    width = 0.65
    p_cured = ax.bar(x, top10_desc['Cured'], width, label='Cured / Recovered', color='#2ecc71')
    p_active = ax.bar(x, top10_desc['Active'], width, bottom=top10_desc['Cured'], label='Active Cases', color='#f39c12')
    p_deaths = ax.bar(x, top10_desc['Deaths'], width, bottom=top10_desc['Cured'] + top10_desc['Active'], label='Deaths', color='#e74c3c')

    ax.set_title("Case Distribution (Active vs Recovered vs Deaths) - Top 10 States", fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(top10_desc['State'], rotation=35, ha='right', fontsize=10)
    ax.set_ylabel("Number of Cases", fontsize=11)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda val, loc: f"{int(val):,}"))
    ax.legend(frameon=True, facecolor='white', loc='upper right')
    p3 = os.path.join(figures_dir, 'active_vs_recovered_comparison.png')
    plt.savefig(p3, bbox_inches='tight')
    plt.close()
    print(f"Saved: {p3}")

    # =========================================================================
    # 4. State-wise Recovery vs Case Fatality Rate (Scatter Analysis)
    # =========================================================================
    # Filter states with >= 5,000 confirmed cases for statistically reliable rates
    filtered_states = latest_states[latest_states['Confirmed'] >= 5000].copy()
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    
    scatter = ax.scatter(
        filtered_states['Recovery_Rate_Pct'],
        filtered_states['Mortality_Rate_Pct'],
        s=filtered_states['Confirmed'] / 1500,
        c=filtered_states['Active'],
        cmap='viridis',
        alpha=0.75,
        edgecolors='black',
        linewidth=1
    )
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Active Cases', fontsize=10)
    cbar.formatter = plt.FuncFormatter(lambda x, loc: f"{int(x):,}")
    cbar.update_ticks()

    for _, row in filtered_states.iterrows():
        ax.annotate(row['State'], (row['Recovery_Rate_Pct'], row['Mortality_Rate_Pct']),
                    xytext=(4, 4), textcoords='offset points', fontsize=8, alpha=0.9)

    ax.set_title("Recovery Rate vs Case Fatality Rate (States with Confirmed >= 5,000)", fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("Recovery Rate (%)", fontsize=11, labelpad=8)
    ax.set_ylabel("Case Fatality Rate (%)", fontsize=11, labelpad=8)
    ax.axvline(filtered_states['Recovery_Rate_Pct'].median(), color='gray', linestyle=':', alpha=0.7, label='Median Recovery Rate')
    ax.axhline(filtered_states['Mortality_Rate_Pct'].median(), color='red', linestyle=':', alpha=0.7, label='Median Fatality Rate')
    ax.legend(loc='lower left', frameon=True)
    p4 = os.path.join(figures_dir, 'recovery_mortality_rates.png')
    plt.savefig(p4, bbox_inches='tight')
    plt.close()
    print(f"Saved: {p4}")

    # =========================================================================
    # 5. National Case Distribution (Donut Chart)
    # =========================================================================
    total_active = latest_states['Active'].sum()
    total_cured = latest_states['Cured'].sum()
    total_deaths = latest_states['Deaths'].sum()

    labels = ['Recovered / Discharged', 'Active Cases', 'Deceased']
    sizes = [total_cured, total_active, total_deaths]
    colors = ['#2ecc71', '#f39c12', '#e74c3c']
    explode = (0.03, 0.03, 0.08)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, autopct='%1.1f%%',
        startangle=140, colors=colors, pctdistance=0.75,
        textprops=dict(color="black", fontsize=11)
    )
    for at in autotexts:
        at.set_fontweight('bold')
        at.set_fontsize(11)

    centre_circle = plt.Circle((0, 0), 0.55, fc='white')
    ax.add_artist(centre_circle)
    ax.set_title(f"National COVID-19 Outcome Distribution\nTotal Cases: {sum(sizes):,}", fontsize=14, fontweight='bold', pad=20)
    p5 = os.path.join(figures_dir, 'national_case_distribution.png')
    plt.savefig(p5, bbox_inches='tight')
    plt.close()
    print(f"Saved: {p5}")

    # =========================================================================
    # 6. Feature Correlation Heatmap
    # =========================================================================
    corr_cols = ['Confirmed', 'Active', 'Cured', 'Deaths', 'New_Cases', 'New_Recovered', 'New_Deaths', 'Recovery_Rate_Pct', 'Mortality_Rate_Pct']
    corr_matrix = df[corr_cols].corr()

    fig, ax = plt.subplots(figsize=(9, 7), dpi=300)
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', cbar=True, ax=ax, linewidths=0.5, square=True)
    ax.set_title("Correlation Heatmap of Epidemiological Features", fontsize=13, fontweight='bold', pad=15)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    p6 = os.path.join(figures_dir, 'correlation_heatmap.png')
    plt.savefig(p6, bbox_inches='tight')
    plt.close()
    print(f"Saved: {p6}")

    print("\nAll EDA visualizations successfully generated!")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(base_dir, 'data', 'covid19_cleaned.csv')
    fig_dir = os.path.join(base_dir, 'figures')
    generate_eda(data_file, fig_dir)
