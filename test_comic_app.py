import pandas as pd
import pytest
from collections import Counter


from encyclopedia import (
    ComicsDatasetManager,
    ComicSearchService,
    handle_special_characters,
    format_multivalue
)


@pytest.fixture
def csv_files(tmp_path):
    # Create a temporary CSV file for records.csv
    records_data = (
        "BL record ID,Title_rec,Date of publication_rec,Genre_rec,ISBN_rec\n"
        "1,Test Comic,2000,Fantasy,12345\n"
        "2,Other Comic,2001,Horror,67890\n"
        "3,Ignore Me,2002,Romance,00000\n"  # This record should be filtered out (Romance not permitted)
    )
    records_file = tmp_path / "records.csv"
    records_file.write_text(records_data)

    # Create a temporary CSV file for titles.csv.
    titles_data = (
        "BL record ID,Title_tit\n"
        "1,Test Comic Title\n"
        "2,Other Comic Title\n"
        "3,Ignore Title\n"
    )
    titles_file = tmp_path / "titles.csv"
    titles_file.write_text(titles_data)

    # Create a temporary CSV file for names.csv.
    names_data = (
        "BL record ID,Name\n"
        "1,Author One\n"
        "1,Author One Duplicate\n"
        "2,Author Two\n"
        "3,Author Three\n"
    )
    names_file = tmp_path / "names.csv"
    names_file.write_text(names_data)

    # Return paths as strings (because your code uses file path strings)
    return str(records_file), str(titles_file), str(names_file)

#ComicsDatasetManager

def test_comics_dataset_manager(csv_files):
    records_file, titles_file, names_file = csv_files
    manager = ComicsDatasetManager(
        recs_filepath=records_file,
        titles_filepath=titles_file,
        authors_filepath=names_file
    )
    df = manager.full_data

    # Check that the DataFrame is not empty.
    assert not df.empty, "The merged DataFrame should not be empty."

    # Only permitted genres are kept (Fantasy, Horror, Science Fiction).
    # The third record (Romance) should be filtered out.
    assert (df["Genre"].isin(["Fantasy", "Horror", "Science Fiction"])).all(), "Only permitted genres should be present."

    # Check that the first row has the expected values.
    row1 = df[df["BL record ID"] == 1].iloc[0]
    assert row1["Title"] == "Test Comic", "Title should come from Title_rec."
    # Since multiple authors are grouped, verify that the Name column concatenates them.
    assert row1["Name"] == "Author One; Author One Duplicate", "Authors should be concatenated."


@pytest.fixture
def sample_dataframe():
    data = {
        "Title": ["Spider-Man", "Batman", "Superman"],
        "Name": ["Stan Lee", "Bob Kane", "Jerry Siegel"],
        "Date of publication": [1962, 1939, 1938],
        "Genre": ["Fantasy", "Horror", "Science Fiction"],
        "ISBN": ["111", "222", "333"]
    }
    return pd.DataFrame(data)

#ComicSearchService

def test_sort_by_title(sample_dataframe):
    service = ComicSearchService(sample_dataframe)
    sorted_df = service.sort_by_title(sample_dataframe, ascending=True)
    sorted_titles = list(sorted_df["Title"])
    expected_titles = sorted(sample_dataframe["Title"].tolist())
    assert sorted_titles == expected_titles, "Titles should be sorted in ascending order."

def test_manual_search(sample_dataframe):
    service = ComicSearchService(sample_dataframe)
    # A search with "man" (case-insensitive) should return all comics.
    results = service.manual_search("man")
    assert len(results) == 3, "Should find all comics containing 'man'."
    
    # A search for "bat" should return only "Batman".
    results = service.manual_search("bat")
    assert len(results) == 1, "Should find only one comic for 'bat'."
    assert results.iloc[0]["Title"] == "Batman", "The found title should be 'Batman'."

def test_advanced_search(sample_dataframe):
    service = ComicSearchService(sample_dataframe)
    # Advanced search: filter by Name containing "Bob"
    results = service.advanced_search({"Name": "Bob"})
    assert len(results) == 1, "Advanced search should find one comic with 'Bob' as author."
    assert results.iloc[0]["Title"] == "Batman", "The found title should be 'Batman'."

def test_filter_by_genre(sample_dataframe):
    service = ComicSearchService(sample_dataframe)
    # Filter by a specific genre that exists (e.g., Fantasy)
    fantasy_df = service.filter_by_genre("Fantasy")
    assert not fantasy_df.empty, "Filtering by Fantasy should return results."
    assert all(fantasy_df["Genre"] == "Fantasy"), "All rows should have Genre 'Fantasy'."
    
    # Filter by a genre that does not exist (e.g., "Nonexistent")
    nonexistent_df = service.filter_by_genre("Nonexistent")
    assert nonexistent_df.empty, "Filtering by a non-existent genre should return an empty DataFrame."
    
    # When 'All' is selected, the full data should be returned.
    all_df = service.filter_by_genre("All")
    assert len(all_df) == len(sample_dataframe), "'All' should return the entire dataset."

def test_generate_report_data(sample_dataframe):
    service = ComicSearchService(sample_dataframe)
    # Simulate some search history and comic frequencies.
    # Let's assume "Batman" was searched a lot (frequency > 100)
    service.query_history = ["Batman", "Batman", "Spider-Man", "Batman"]
    service.comic_frequency = Counter({"Batman": 120, "Spider-Man": 10, "Superman": 5})
    
    report = service.generate_report_data()
    
    # Check that the report includes the header for popular comics.
    assert "Comics appearing in over 100 searches:" in report, "Report should include a section for popular comics."
    # Since Batman has a frequency of 120 (>100), it should appear.
    assert "Batman" in report, "Batman should appear in the popular comics section."
    
    # Also check that the top search queries and top results sections are present.
    assert "Top 10 search queries:" in report, "Report should include a section for top search queries."
    assert "Top 10 search results:" in report, "Report should include a section for top search results."


# Test utility functions

def test_handle_special_characters():
    # Check that regular text remains unchanged.
    assert handle_special_characters("Café") == "Café"
    # Check that pd.NA or None returns an empty string.
    assert handle_special_characters(pd.NA) == ""
    assert handle_special_characters(None) == ""

def test_format_multivalue():
    # Test with a semicolon-separated string.
    input_value = "val1; val2; val3"
    expected = "Test: val1 | Test: val2 | Test: val3"
    assert format_multivalue("Test", input_value) == expected
    # Test with a string that does not require formatting.
    assert format_multivalue("Test", "single_value") == "single_value"
