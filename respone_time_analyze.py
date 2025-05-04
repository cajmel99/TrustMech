from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import os
import re
import seaborn as sns

folder_path = Path("mechanics_services_GET")

file_paths = {
    10: folder_path / "results_c10.csv",
    50: folder_path / "results_c50.csv",
    100: folder_path / "results_c100.csv",
    250: folder_path / "results_c250.csv",
    500: folder_path / "results_c500.csv",
}
column_names = ["Percentile", "Time"]

percentile_99 = {}

for conc_level, path in sorted(file_paths.items()):
    df = pd.read_csv(path, skiprows=1, names=column_names)
    row_99 = df[df["Percentile"].astype(float) == 99.0]
    if not row_99.empty:
        percentile_99[conc_level] = row_99["Time"].values[0]

# Tworzenie DataFrame i wykresu
df_percentiles = pd.DataFrame.from_dict(percentile_99, orient='index', columns=['99th Percentile'])
df_percentiles.index.name = 'Concurrency Level'
df_percentiles.sort_index(inplace=True)

# Wykres
plt.figure(figsize=(10, 6))
sns.lineplot(data=df_percentiles, x=df_percentiles.index, y='99th Percentile', marker='o')
plt.title('99. percentyl czasu odpowiedzi vs poziom współbieżności')
plt.xlabel('Poziom współbieżności (ab -c)')
plt.ylabel('Czas odpowiedzi [ms] (99. percentyl)')
plt.grid(True)
plt.tight_layout()
plt.show()
