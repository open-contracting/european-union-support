namespace :label do
  task :xpath do
    FileUtils.mkdir_p('output/mapping')

    files('output/samples/F{}_*.xml').each do |filename|
      basename = File.basename(filename, '.xml')
      path = "output/mapping/#{basename}.csv"

      rows_by_xpath = {}
      if File.exist?(path)
        CSV.read(path, headers: true).each do |row|
          rows_by_xpath[row['xpath']] = row
        end
      end

      xpaths = Set.new
      Nokogiri::XML(File.read(filename)).xpath("/#{basename}//*").each do |element|
        xpath = element.path.gsub(/\[\d+\]/, '').gsub(%r{\b(?:choice|group|sequence)/}, '')
        if !%w(choice group sequence P).include?(xpath.split('/')[-1])
          xpaths << xpath
        end
      end

      # Preserve the label-key and index columns, if a file existed.
      CSV.open(path, 'w') do |csv|
        csv << ['xpath', 'label-key', 'index', 'comment']
        xpaths.each do |xpath|
          csv << (rows_by_xpath[xpath] || [xpath, nil, nil, nil])
        end
      end
    end
  end

  task :ignore do
    path = 'output/mapping/ignore.csv'
    non_default_keys = []
    if File.exist?(path)
      CSV.read(path, headers: true).each do |row|
        if !row['label-key'][/\AHD?_/]
          non_default_keys << row
        end
      end
    end

    keys = Set.new
    files('source/*_TED_forms_templates/F{}_*.pdf').each do |filename|
      keys += `pdftotext -layout #{filename} -`.scan(/<<([^>]+)>>/).flatten.select{ |key| key[/\AHD?_/] }
    end

    CSV.open(path, 'w') do |csv|
      csv << ['label-key', 'index']
      keys.each do |key|
        csv << [key, nil]
      end
      non_default_keys.each do |row|
        csv << row
      end
    end
  end
end
