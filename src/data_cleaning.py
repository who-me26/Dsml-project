"""
data_cleaning.py
----------------
Automated data cleaning and preprocessing pipeline for COVID-19 India dataset.
Handles:
  1. Standardizing state and union territory names (resolving typos, asterisks, prefix variations).
  2. Imputing faulty coordinates (e.g., (0.0, 0.0) anomalies).
  3. Cleaning non-numeric characters in numerical fields (e.g., '0#' in Death).
  4. Type casting to appropriate integer and datetime data types.
  5. Rectifying negative daily deltas resulting from state reporting adjustments.
  6. Engineering derived epidemiological metrics:
     - Active cases = Total Confirmed - Cured - Death
     - Recovery Rate (%) = (Cured / Total Confirmed) * 100
     - Mortality / Case Fatality Rate (%) = (Death / Total Confirmed) * 100
     - 7-day rolling moving averages of new cases, deaths, and recoveries.
  7. Exporting clean transactional data and latest state-level aggregation summaries.
"""

import os
import pandas as pd
import numpy as np

def clean_covid_data(input_path: str, output_path: str, summary_path: str):
    print(f"Loading raw dataset from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"Initial shape: {df.shape}")

    # 1. Parse Date
    df['Date'] = pd.to_datetime(df['Date'])

    # 2. Standardize State/UT Names
    state_mapping = {
        'Telengana': 'Telangana',
        'Telangana***': 'Telangana',
        'Union Territory of Ladakh': 'Ladakh',
        'Union Territory of Jammu and Kashmir': 'Jammu and Kashmir',
        'Union Territory of Chandigarh': 'Chandigarh',
        'Dadar Nagar Haveli': 'Dadra and Nagar Haveli and Daman and Diu',
        'Dadra and Nagar Haveli': 'Dadra and Nagar Haveli and Daman and Diu',
        'Daman & Diu': 'Dadra and Nagar Haveli and Daman and Diu',
        'Daman and Diu': 'Dadra and Nagar Haveli and Daman and Diu'
    }
    df['State'] = df['Name of State / UT'].str.strip().replace(state_mapping)

    # 3. Coordinate standardization
    # Reference coordinates for states with anomalies (e.g. Telangana had 0.0, 0.0 on some dates)
    state_coords = df[df['Latitude'] > 0].groupby('State')[['Latitude', 'Longitude']].mean().to_dict('index')
    # Default for Telangana if missing
    if 'Telangana' not in state_coords or state_coords['Telangana']['Latitude'] == 0:
        state_coords['Telangana'] = {'Latitude': 18.1124, 'Longitude': 79.0193}

    for state, coords in state_coords.items():
        mask = (df['State'] == state) & ((df['Latitude'] == 0) | (df['Longitude'] == 0) | (df['Latitude'].isna()))
        df.loc[mask, 'Latitude'] = coords['Latitude']
        df.loc[mask, 'Longitude'] = coords['Longitude']

    # 4. Clean non-numeric characters and cast types
    # Clean 'Death' column (e.g., '0#')
    df['Death'] = df['Death'].astype(str).str.replace(r'[^0-9]', '', regex=True)
    df['Death'] = pd.to_numeric(df['Death'], errors='coerce').fillna(0).astype('int64')

    # Total Confirmed and Cured
    df['Total Confirmed cases'] = pd.to_numeric(df['Total Confirmed cases'], errors='coerce').fillna(0).astype('int64')
    df['Cured/Discharged/Migrated'] = pd.to_numeric(df['Cured/Discharged/Migrated'], errors='coerce').fillna(0).astype('int64')

    # New daily cases, deaths, recovered
    for col in ['New cases', 'New deaths', 'New recovered']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')
        # Rectify reporting adjustments (e.g., negative delta values clipped to 0)
        df[col] = df[col].clip(lower=0)

    # Rename columns to clean, pythonic format
    rename_dict = {
        'Total Confirmed cases': 'Confirmed',
        'Death': 'Deaths',
        'Cured/Discharged/Migrated': 'Cured',
        'New cases': 'New_Cases',
        'New deaths': 'New_Deaths',
        'New recovered': 'New_Recovered'
    }
    df = df.rename(columns=rename_dict)

    # Drop old uncleaned state column
    df = df.drop(columns=['Name of State / UT'])

    # 5. Calculate epidemiological metrics
    # Active = Confirmed - Cured - Deaths (clipped to 0 if rounding/lag causes minor negatives)
    df['Active'] = (df['Confirmed'] - df['Cured'] - df['Deaths']).clip(lower=0)
    
    # Recovery and Mortality Rates
    df['Recovery_Rate_Pct'] = np.where(df['Confirmed'] > 0, (df['Cured'] / df['Confirmed']) * 100, 0.0).round(2)
    df['Mortality_Rate_Pct'] = np.where(df['Confirmed'] > 0, (df['Deaths'] / df['Confirmed']) * 100, 0.0).round(2)

    # Sort sequentially
    df = df.sort_values(by=['State', 'Date']).reset_index(drop=True)

    # Calculate 7-day rolling moving averages per state
    df['New_Cases_7d_MA'] = df.groupby('State')['New_Cases'].transform(lambda x: x.rolling(7, min_periods=1).mean().round(1))
    df['New_Deaths_7d_MA'] = df.groupby('State')['New_Deaths'].transform(lambda x: x.rolling(7, min_periods=1).mean().round(1))
    df['New_Recovered_7d_MA'] = df.groupby('State')['New_Recovered'].transform(lambda x: x.rolling(7, min_periods=1).mean().round(1))

    # Reorder columns logically
    final_cols = [
        'Date', 'State', 'Latitude', 'Longitude',
        'Confirmed', 'Active', 'Cured', 'Deaths',
        'New_Cases', 'New_Deaths', 'New_Recovered',
        'New_Cases_7d_MA', 'New_Deaths_7d_MA', 'New_Recovered_7d_MA',
        'Recovery_Rate_Pct', 'Mortality_Rate_Pct'
    ]
    df = df[final_cols]

    # Save cleaned time-series dataset
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Cleaned dataset saved to: {output_path} (Shape: {df.shape})")

    # 6. Generate State-Level Latest Summary Table
    latest_date = df['Date'].max()
    latest_df = df[df['Date'] == latest_date].copy()
    
    state_summary = latest_df[[
        'State', 'Confirmed', 'Active', 'Cured', 'Deaths',
        'Recovery_Rate_Pct', 'Mortality_Rate_Pct'
    ]].sort_values(by='Confirmed', ascending=False).reset_index(drop=True)

    state_summary.to_csv(summary_path, index=False)
    print(f"Latest state summary (as of {latest_date.strftime('%Y-%m-%d')}) saved to: {summary_path}")

    # Print summary statistics
    print("\n--- Summary as of " + latest_date.strftime('%Y-%m-%d') + " ---")
    print(f"Total States/UTs Reported: {len(state_summary)}")
    print(f"National Total Confirmed: {state_summary['Confirmed'].sum():,}")
    print(f"National Total Active:    {state_summary['Active'].sum():,}")
    print(f"National Total Recovered: {state_summary['Cured'].sum():,}")
    print(f"National Total Deaths:    {state_summary['Deaths'].sum():,}")
    overall_recovery = (state_summary['Cured'].sum() / state_summary['Confirmed'].sum()) * 100
    overall_mortality = (state_summary['Deaths'].sum() / state_summary['Confirmed'].sum()) * 100
    print(f"National Recovery Rate:   {overall_recovery:.2f}%")
    print(f"National Mortality Rate:  {overall_mortality:.2f}%")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    in_file = os.path.join(base_dir, 'data', 'covid19_raw.csv')
    out_file = os.path.join(base_dir, 'data', 'covid19_cleaned.csv')
    sum_file = os.path.join(base_dir, 'data', 'state_summary.csv')
    clean_covid_data(in_file, out_file, sum_file)
