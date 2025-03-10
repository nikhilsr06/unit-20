import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from collections import Counter

##########################################################################################################
# Data Class
##########################################################################################################

class ComicsDatasetManager:
    """
    Responsible for loading, cleaning, and merging CSV data.
    """
    def __init__(self, recs_filepath="records.csv", titles_filepath="titles.csv", authors_filepath="names.csv"):
        self.recs_filepath = recs_filepath
        self.titles_filepath = titles_filepath
        self.authors_filepath = authors_filepath
        self.full_data = pd.DataFrame()
        self.load_data()

    def load_data(self):
        """
        Load CSV files, merge them, clean columns, and restrict to allowed genres.
        """
        try:
            # Load CSV files
            recs_dataframe = pd.read_csv(self.recs_filepath, encoding="utf-8")
            titles_dataframe = pd.read_csv(self.titles_filepath, encoding="utf-8")
            authors_dataframe = pd.read_csv(self.authors_filepath, encoding="utf-8")
            
            # Clean column names
            recs_dataframe.columns = recs_dataframe.columns.str.strip()
            titles_dataframe.columns = titles_dataframe.columns.str.strip()
            authors_dataframe.columns = authors_dataframe.columns.str.strip()
            
            id_key = "BL record ID"
            # Merge records and titles with custom suffixes
            merge_temp = pd.merge(
                recs_dataframe,
                titles_dataframe,
                on=id_key,
                how="left",
                suffixes=('_rec', '_tit')
            )
            # Create unified columns
            merge_temp["Title"] = merge_temp["Title_rec"]
            merge_temp["Date of publication"] = merge_temp["Date of publication_rec"]
            merge_temp["Genre"] = merge_temp["Genre_rec"]
            merge_temp["ISBN"] = merge_temp["ISBN_rec"].fillna("missing")
            if "Languages_rec" in merge_temp.columns:
                merge_temp["Languages"] = merge_temp["Languages_rec"]
            if "Type of name_rec" in merge_temp.columns:
                merge_temp["Type of name"] = merge_temp["Type of name_rec"]
            
            # Group names by BL record ID and merge
            grouped_authors = authors_dataframe.groupby(id_key)["Name"].apply(
                lambda names: "; ".join(names.dropna().unique())
            ).reset_index()
            self.full_data = pd.merge(merge_temp, grouped_authors, on=id_key, how="left")
            
            # Process special characters in key fields
            for col in ["Title", "Name", "Genre"]:
                if col in self.full_data.columns:
                    self.full_data[col] = self.full_data[col].apply(handle_special_characters)
            
            # Process multi-value fields if present (example: Topics)
            if "Topics" in self.full_data.columns:
                self.full_data["Topics"] = self.full_data["Topics"].apply(
                    lambda x: format_multivalue("Topics", x)
                )
            
            # Restrict data to allowed genres only
            permitted_genres = ["Fantasy", "Horror", "Science Fiction"]
            self.full_data = self.full_data[self.full_data["Genre"].isin(permitted_genres)]
            
            print("Merged DataFrame preview:")
            print(self.full_data.head())
            
        except Exception as err:
            messagebox.showerror("Error", f"Failed to load data: {err}")
            self.full_data = pd.DataFrame()

##########################################################################################################
# Search Class
##########################################################################################################

class ComicSearchService:
    """
    Provides methods for filtering, sorting, and searching within the comic data.
    Also tracks search queries and result frequencies.
    """
    def __init__(self, full_df: pd.DataFrame):
        self.full_data = full_df
        self.query_history = []  # list of search queries
        self.comic_frequency = Counter()  # counts how many times a comic appears in search results

    def filter_by_genre(self, genre: str) -> pd.DataFrame:
        """
        Filter data by genre.
        """
        if genre != "All":
            return self.full_data[self.full_data["Genre"] == genre]
        return self.full_data.copy()

    def sort_by_title(self, df: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
        """
        Sort data by title using quick sort.
        """
        def qsort(items):
            if len(items) < 2:
                return items
            pivot = items[0]
            less = [i for i in items[1:] if i <= pivot]
            greater = [i for i in items[1:] if i > pivot]
            return qsort(less) + [pivot] + qsort(greater)

        title_list = list(df["Title"])
        sorted_title_list = qsort(title_list)
        if not ascending:
            sorted_title_list.reverse()
        sorted_dataframe = df.set_index("Title").loc[sorted_title_list].reset_index()
        return sorted_dataframe

    def manual_search(self, query_str: str) -> pd.DataFrame:
        """
        Search for comics by title (case-insensitive) and track the search query and results.
        """
        if not query_str:
            return self.full_data.copy()
        search_mask = self.full_data["Title"].str.lower().str.contains(query_str.lower(), na=False)
        found_results = self.full_data[search_mask]
        self.query_history.append(query_str)
        for comic in found_results["Title"]:
            self.comic_frequency[comic] += 1
        return found_results

    def advanced_search(self, search_params: dict) -> pd.DataFrame:
        """
        Perform an advanced search using multiple parameters.
        """
        filtered_df = self.full_data.copy()
        for col, value in search_params.items():
            if value:
                col_mask = filtered_df[col].astype(str).str.lower().str.contains(value.lower(), na=False)
                filtered_df = filtered_df[col_mask]
        combined_query = ', '.join([f"{k}={v}" for k, v in search_params.items() if v])
        if combined_query:
            self.query_history.append(combined_query)
            for comic in filtered_df["Title"]:
                self.comic_frequency[comic] += 1
        return filtered_df

    def generate_report_data(self) -> str:
        """
        Generate and return a formatted report with:
          - Comics appearing in over 100 searches,
          - Top 10 search queries,
          - Top 10 search results.
        """
        popular_comics = [comic for comic, count in self.comic_frequency.items() if count > 100]
        top_queries = [q for q, _ in Counter(self.query_history).most_common(10)]
        top_results = [comic for comic, _ in self.comic_frequency.most_common(10)]
        
        report_contents = []
        report_contents.append("--------- Search Report ---------\n\n")
        
        report_contents.append("Comics appearing in over 100 searches:\n")
        if popular_comics:
            for comic in popular_comics:
                report_contents.append(f"  - {comic}\n")
        else:
            report_contents.append("  None\n")
            
        report_contents.append("\nTop 10 search queries:\n")
        if top_queries:
            for query in top_queries:
                report_contents.append(f"  - {query}\n")
        else:
            report_contents.append("  None\n")
            
        report_contents.append("\nTop 10 search results:\n")
        if top_results:
            for result in top_results:
                report_contents.append(f"  - {result}\n")
        else:
            report_contents.append("  None\n")
            
        return "".join(report_contents)

##########################################################################################################
# Tkinter
##########################################################################################################

class ComicAppUI:
    """
    Main application class responsible for creating the GUI and interacting with
    data and search services.
    """
    def __init__(self, root_window):
        self.root_window = root_window
        root_window.title("Comic Encyclopedia")
        root_window.geometry("900x600")
        
        # Initialize data and search services.
        self.dataset_manager = ComicsDatasetManager()
        self.searcher = ComicSearchService(self.dataset_manager.full_data)
        self.current_results = pd.DataFrame()  # current search results
        self.stored_results = pd.DataFrame()  # stored saved searches
        
        self.setup_widgets()
        self.display_results(self.dataset_manager.full_data)

    def setup_widgets(self):
        """
        Create and layout all GUI components.
        """
        self.build_top_container()
        self.build_mid_container()
        self.build_bottom_container()

    def build_top_container(self):
        """
        Create the top frame containing filters, sorting, and search inputs.
        """
        top_container = tk.Frame(self.root_window)
        top_container.pack(fill=tk.X, padx=10, pady=5)
        
        # Genre filter dropdown restricted to allowed genres
        tk.Label(top_container, text="Select Genre:").pack(side=tk.LEFT, padx=(0,5))
        genre_options = ["All", "Fantasy", "Horror", "Science Fiction"]
        self.selected_genre = tk.StringVar(value="All")
        self.genre_combo = ttk.Combobox(top_container, textvariable=self.selected_genre, values=genre_options, state="readonly")
        self.genre_combo.pack(side=tk.LEFT, padx=(0,15))
        
        # Grouping option dropdown
        tk.Label(top_container, text="Group by:").pack(side=tk.LEFT, padx=(0,5))
        self.selected_group = tk.StringVar(value="Author")
        self.group_combo = ttk.Combobox(top_container, textvariable=self.selected_group, 
                                         values=["Author", "Year of Publication"], state="readonly")
        self.group_combo.pack(side=tk.LEFT, padx=(0,15))
        
        # Apply Filters Button
        tk.Button(top_container, text="Apply Filters", command=self.filters).pack(side=tk.LEFT, padx=(0,15))
        
        # Sorting Buttons
        sort_container = tk.Frame(top_container)
        sort_container.pack(side=tk.LEFT, padx=(0,15))
        tk.Label(sort_container, text="Sort Titles:").pack(side=tk.LEFT)
        tk.Button(sort_container, text="A-Z", command=lambda: self.sort_results(True)).pack(side=tk.LEFT, padx=5)
        tk.Button(sort_container, text="Z-A", command=lambda: self.sort_results(False)).pack(side=tk.LEFT, padx=5)
        
        # Manual search components
        tk.Label(top_container, text="Title Search:").pack(side=tk.LEFT, padx=(0,5))
        self.title_query = tk.StringVar()
        self.title_input = tk.Entry(top_container, textvariable=self.title_query, width=20)
        self.title_input.pack(side=tk.LEFT, padx=(0,5))
        tk.Button(top_container, text="Search", command=self.manual_search).pack(side=tk.LEFT)
        tk.Button(top_container, text="Advanced Search", command=self.advanced_search).pack(side=tk.LEFT, padx=(10,0))
        
        # Report Button
        tk.Button(top_container, text="Generate Report", command=self.show_report)\
            .pack(side=tk.LEFT, padx=(10,0))

    def build_mid_container(self):
        """
        Create the middle frame containing the results treeview.
        """
        mid_container = tk.Frame(self.root_window)
        mid_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.results_treeview = ttk.Treeview(mid_container, 
                                             columns=("Title", "Name", "Date", "Genre", "ISBN"), 
                                             show="headings")
        self.results_treeview.heading("Title", text="Title")
        self.results_treeview.heading("Name", text="Author(s)")
        self.results_treeview.heading("Date", text="Year")
        self.results_treeview.heading("Genre", text="Genre")
        self.results_treeview.heading("ISBN", text="ISBN")
        
        vsb = ttk.Scrollbar(mid_container, orient="vertical", command=self.results_treeview.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_treeview.configure(yscrollcommand=vsb.set)
        self.results_treeview.pack(fill=tk.BOTH, expand=True)

    def build_bottom_container(self):
        """
        Create the bottom frame with action buttons.
        """
        bottom_container = tk.Frame(self.root_window)
        bottom_container.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(bottom_container, text="Clear Search", command=self.clear_search).pack(side=tk.LEFT, padx=5)
        tk.Button(bottom_container, text="Save Selected", command=self.save_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(bottom_container, text="Show Saved", command=self.show_saved_searches).pack(side=tk.LEFT, padx=5)

    
    # Search, Filter, and Sort Methods
    
    def filters(self):
        """
        Filter dataset based on selected genre and grouping option.
        """
        filtered_df = self.dataset_manager.full_data.copy()
        genre_choice = self.selected_genre.get()
        if genre_choice != "All":
            filtered_df = filtered_df[filtered_df["Genre"] == genre_choice]
        # Grouping by Year of Publication (if selected) sorts by that column
        group_option = self.selected_group.get()
        if group_option == "Year of Publication" and "Date of publication" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("Date of publication")
        self.current_results = filtered_df
        self.display_results(filtered_df)

    def sort_results(self, ascending: bool = True):
        """
        Sort the current search results by title.
        """
        if self.current_results.empty:
            messagebox.showinfo("Info", "No search results to sort. Please apply a filter or search first.")
            return
        sorted_dataframe = self.searcher.sort_by_title(self.current_results, ascending=ascending)
        self.current_results = sorted_dataframe
        self.display_results(sorted_dataframe)

    def manual_search(self):
        """
        Search comics by title using a manual search.
        """
        query_text = self.title_query.get().strip()
        if not query_text:
            messagebox.showinfo("Info", "Enter a title to search for.")
            return
        found_results = self.searcher.manual_search(query_text)
        self.current_results = found_results
        self.display_results(found_results)

    def advanced_search(self):
        """
        Open an advanced search window allowing multiple search parameters.
        """
        adv_window = tk.Toplevel(self.root_window)
        adv_window.title("Advanced Search")
        adv_window.geometry("400x300")
        param_mapping = {
            "Author": "Name",
            "Publication Year": "Date of publication",
            "Genre": "Genre",
            "Edition Languages": "Languages",
            "Name Type": "Type of name"
        }
        entries = {}
        row_index = 0
        for label_text, col_key in param_mapping.items():
            tk.Label(adv_window, text=f"{label_text}:").grid(row=row_index, column=0, sticky=tk.W, padx=10, pady=5)
            entry_widget = tk.Entry(adv_window, width=30)
            entry_widget.grid(row=row_index, column=1, padx=10, pady=5)
            entries[col_key] = entry_widget
            row_index += 1
        
        def perform_adv_search():
            adv_params = {col: entry.get().strip() for col, entry in entries.items()}
            results_adv = self.searcher.advanced_search(adv_params)
            self.current_results = results_adv
            self.display_results(results_adv)
            adv_window.destroy()
        
        tk.Button(adv_window, text="Search", command=perform_adv_search)\
            .grid(row=row_index, column=0, columnspan=2, pady=15)

    def display_results(self, df: pd.DataFrame):
        """
        Clear the treeview and display rows from the dataframe.
        """
        self.results_treeview.delete(*self.results_treeview.get_children())
        for _, row_data in df.iterrows():
            comic_title = handle_special_characters(row_data.get("Title", ""))
            comic_author = handle_special_characters(row_data.get("Name", ""))
            publication_year = row_data.get("Date of publication", "")
            comic_genre = handle_special_characters(row_data.get("Genre", ""))
            comic_isbn = row_data.get("ISBN", "missing")
            self.results_treeview.insert("", tk.END, values=(comic_title, comic_author, publication_year, comic_genre, comic_isbn))

    def clear_search(self):
        """
        Clear search results and reset filters.
        """
        self.current_results = pd.DataFrame()
        self.title_query.set("")
        self.selected_genre.set("All")
        self.selected_group.set("Author")
        self.display_results(self.dataset_manager.full_data)

    def save_selected(self):
        """
        Save the currently selected items.
        """
        selected_entries = self.results_treeview.selection()
        if not selected_entries:
            messagebox.showinfo("Info", "No items selected to save.")
            return
        
        selected_rows = []
        for entry in selected_entries:
            values = self.results_treeview.item(entry, "values")
            entry_data = {
                "Title": values[0],
                "Name": values[1],
                "Date of publication": values[2],
                "Genre": values[3],
                "ISBN": values[4]
            }
            selected_rows.append(entry_data)
        if selected_rows:
            temp_df = pd.DataFrame(selected_rows)
            self.stored_results = pd.concat([self.stored_results, temp_df], ignore_index=True)
            messagebox.showinfo("Info", "Selected items saved to your search list.")

    def show_saved_searches(self):
        """
        Display the saved searches in a new window.
        """
        if self.stored_results.empty:
            messagebox.showinfo("Info", "No saved searches.")
            return
        
        saved_window = tk.Toplevel(self.root_window)
        saved_window.title("Saved Searches")
        saved_window.geometry("600x400")
        saved_treeview = ttk.Treeview(saved_window, columns=("Title", "Name", "Date of publication", "Genre", "ISBN"), show="headings")
        saved_treeview.heading("Title", text="Title")
        saved_treeview.heading("Name", text="Name")
        saved_treeview.heading("Date of publication", text="Year")
        saved_treeview.heading("Genre", text="Genre")
        saved_treeview.heading("ISBN", text="ISBN")
        saved_treeview.pack(fill=tk.BOTH, expand=True)
        
        for _, row_data in self.stored_results.iterrows():
            saved_treeview.insert("", tk.END, values=(row_data["Title"], row_data["Name"], row_data["Date of publication"], row_data["Genre"], row_data["ISBN"]))

    def show_report(self):
        """
        Display the search report in a new window with a scrollable text widget.
        """
        report_text = self.searcher.generate_report_data()
        report_window = tk.Toplevel(self.root_window)
        report_window.title("Search Report")
        report_window.geometry("600x400")
        
        text_container = tk.Frame(report_window)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        report_text_widget = tk.Text(text_container, wrap="word", font=("Courier", 10), yscrollcommand=scrollbar.set)
        report_text_widget.insert("1.0", report_text)
        report_text_widget.config(state="disabled")
        report_text_widget.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=report_text_widget.yview)

##########################################################################################################
# Utility Functions
##########################################################################################################

def format_multivalue(field_name: str, value) -> str:
    """
    Format fields with multiple semi-colon separated values.
    Returns: "field_name: value1 | field_name: value2 | ..."
    """
    if pd.isna(value):
        return "missing" if field_name.lower() == "isbn" else ""
    
    if isinstance(value, str) and ";" in value:
        values_list = [val.strip() for val in value.split(";") if val.strip()]
        return " | ".join([f"{field_name}: {val}" for val in values_list])
    
    return value

def handle_special_characters(txt) -> str:
    """
    Process text to handle special characters.
    """
    if pd.isna(txt):
        return ""
    try:
        return str(txt.encode('utf-8', 'replace').decode('utf-8'))
    except Exception:
        return str(txt)

##########################################################################################################
# Run App
##########################################################################################################

if __name__ == "__main__":
    root = tk.Tk()
    app = ComicAppUI(root)
    root.mainloop()
