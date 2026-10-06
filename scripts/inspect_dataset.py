from backend.app.data_processing.dataset_inspector import detect_dataset, inspect_dataset


def main() -> None:
    dataset = detect_dataset('data/raw')
    if not dataset:
        print('Dataset not detected in data/raw/.')
        return
    print(inspect_dataset(dataset))


if __name__ == '__main__':
    main()
