# Helper to write raw data accurately
import os

raw_csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'covid19_raw.csv')
print("Target path:", os.path.abspath(raw_csv_path))
