namespace :label do
  task :xpath do
    # generate CSV files with all XPaths for each form, preserving the label-key column, and adding an index column for the PDF's indices
  end

  task :ignore do
    # generate ignore CSV, preserving non H_ and HD_ keys
  end
end

# TODO:
# Do the process below
# Commit updated files to git
# Use the XPath CSVs generate table with columns for indices, labels (using XLSX file) and XML elements
