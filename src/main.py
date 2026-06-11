from datasets import load_datasets


def main():
    df = load_datasets()
    print(df[["CountryCode", "date", "observed_new_cases", "Rt"]])


if __name__ == "__main__":
    main()
