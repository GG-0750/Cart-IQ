from backend.app.data_processing.processor import process_real_dataset


def main() -> None:
    result = process_real_dataset(sample_rows=200000)
    print(result)


if __name__ == '__main__':
    main()
