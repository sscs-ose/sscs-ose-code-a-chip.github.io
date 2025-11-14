from typing import Sequence, Tuple, Optional
import os
import pandas as pd


def extract_truth_table(file_path: str,
                      usecols: Optional[Sequence[str]] = ("A", "B", "OUT"),
                      sep: Optional[str] = None) -> pd.DataFrame:

    if sep is None:
        sep = r"\s+"

    # read_csv with engine='python' supports regex separator
    df = pd.read_csv(file_path, sep=sep, engine="python", comment="#",
                     header=0)

    # Normalize column names (strip spaces)
    df.columns = [c.strip() for c in df.columns]

    if usecols is None:
        return df

    missing = [c for c in usecols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in file: {missing}. Available: {list(df.columns)}")

    return df.loc[:, list(usecols)].copy()


if __name__ == "__main__":

    cwd = os.path.dirname(__file__)
    default_path = os.path.join(cwd, "../code/genetic_algorithm/output/extracted_truth_table.txt")
    df = extract_truth_table(default_path, usecols=("A", "B", "OUT"))
    df.to_csv("code/genetic_algorithm/output/extracted_truth_table.csv", index=False)
