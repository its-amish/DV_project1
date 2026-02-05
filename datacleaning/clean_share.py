import pandas as pd

df = pd.read_csv('sharegpt_travel.csv')

# Filter for confidence score >= 0.45 and remove rows with missing keywords
df_clean = df[(df['confidence_score'] >= 0.45) & (df['matched_keywords'].notna())]

df_clean.to_csv('cleaned_sharegpt_travel.csv', index=False)