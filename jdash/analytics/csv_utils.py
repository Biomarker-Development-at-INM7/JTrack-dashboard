import os

import pandas as pd


def get_csv_display_name(value):
    return os.path.basename(str(value))


def read_selected_csv(value):
    try:
        df = pd.read_csv(value)
        if len(df.columns) == 1 and ";" in str(df.columns[0]):
            return pd.read_csv(value, sep=";")
        return df
    except Exception:
        return pd.read_csv(value, sep=";")
