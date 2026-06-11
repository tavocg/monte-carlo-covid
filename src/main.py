from datasets import DATA_DIR, DATASETS


def main():
    dataset_paths = [DATA_DIR / dataset for dataset in DATASETS]
    print(dataset_paths)


if __name__ == "__main__":
    main()
