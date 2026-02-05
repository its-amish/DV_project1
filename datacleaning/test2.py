import pandas as pd
import glob

# Find the first parquet file
files = glob.glob("*.parquet")
if files:
    print(f"Inspecting: {files[0]}")
    df = pd.read_parquet(files[0])
    print("\n--- COLUMNS ---")
    print(df.columns.tolist())
    
    print("\n--- FIRST ROW (Raw) ---")
    print(df.iloc[0].to_dict())
else:
    print("No .parquet file found in directory.")