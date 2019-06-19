namespace :label do
  desc 'Create or update files for mapping XPath values to corresponding label keys'
  task :xpath do
    FileUtils.mkdir_p('output/mapping')

    files('output/samples/{}*.xml').each do |filename|
      basename = File.basename(filename, '.xml')
      path = "output/mapping/#{basename}.csv"

      rows_by_xpath = {}
      if File.exist?(path)
        CSV.read(path, headers: true).each do |row|
          rows_by_xpath[row['xpath']] = row
        end
      end

      xpaths = Set.new
      Nokogiri::XML(File.read(filename)).xpath("/*//*|/*//@*").each do |element|
        xpath = element.path.sub(/\A\/(F.._2014|MOVE)/, '').gsub(/\[\d+\]/, '').gsub(%r{\b(?:choice|group|sequence)/}, '')
        # Exclude XSD elements, paragraph tags, form identifier, and attributes for empty elements.
        if !%w(choice group sequence P @CODE @CTYPE @FORM @PUBLICATION @TYPE @VALUE).include?(xpath.split('/')[-1])
          xpaths << xpath
        end
      end

      # Preserve the label-key and index columns, if a file existed.
      CSV.open(path, 'w') do |csv|
        csv << ['xpath', 'label-key', 'index', 'comment', 'guidance']
        xpaths.each do |xpath|
          csv << (rows_by_xpath[xpath] || [xpath, nil, nil, nil, nil])
        end
      end
    end
  end

  desc 'Report any CSV quoting errors'
  task :validate do
    files('output/mapping/{}*.csv').each do |filename|
      CSV.foreach(filename, headers: true) do |row|
        if row.size != 5
          raise "#{filename}: #{row['xpath']} unquoted comma!"
        end
      end
    end
  end

  desc 'Report any XPath values without corresponding label keys, and vice versa'
  task :missing do
    label_keys_seen = Set.new(['_or'])
    indices_seen = Set.new

    %w(ignore.csv enumerations.csv additional.csv).each do |basename|
      CSV.read(File.join('output', 'mapping', basename), headers: true).each do |row|
        label_keys_seen << row['label-key']
        indices_seen << row['index']
      end
    end

    files('output/mapping/{}*.csv').each do |filename|
      CSV.foreach(filename, headers: true) do |row|
        if row['label-key'].nil?
          if row['comment'].nil? && row['guidance'].nil?
            puts "#{filename}: #{row['xpath']} has no label-key, comment or guidance"
          end
        else
          label_keys_seen << row['label-key']
        end
        if row['index']
          indices_seen << row['index']
        end
      end
    end

    form_title_labels = [
      'notice_contract_award', # F03
      'notice_contract_award_sub', # F03
      'notice_award_utilities', # F06
      'notice_contract_award_sub', # F06
      'notice_relates_to', # F08
      'notice_result_design_cont', # F13
      'notice_corrigendum', # F14
      'notice_mod', # F20
      'notice_social_public', # F21
      'notice_social_util', # F22
      'notice_social_concess', # F23
    ]

    regex = /\A(annex_d\d|section_\d|directive_(?:200981|201423|201424|201425)|#{form_title_labels.join('|')})\z/

    files('source/TED_forms_templates_R2.0.9/{}*.pdf').each do |filename|
      text = pdftotext(filename)

      difference = Set.new(label_keys(text).reject{ |key| help_text?(key) || key[regex] }) - label_keys_seen
      if difference.any?
        puts "#{File.basename(filename)}: #{difference.to_a.join(', ')}"
      end

      difference = Set.new(indices(text)) - indices_seen
      if difference.any?
        puts "#{File.basename(filename)}: #{difference.to_a.join(', ')}"
      end
    end
  end

  desc 'Report any notes about mappings'
  task :comments do
    files('output/mapping/{}*.csv').each do |filename|
      CSV.foreach(filename, headers: true) do |row|
        if row['comment']
          puts "#{filename}: %-60s %s" % [row['xpath'], row['comment']]
        end
      end
    end
  end

  desc 'Add form numbers to ignore.csv'
  task :ignore do
    # Some form titles are used on later forms and therefore ignored with ignore.csv.
    ignore = {
      '01' => ['notice_pin', 'directive_201424'], # F02
      '02' => ['notice_contract', 'directive_201424'], # F03
      '04' => ['notice_periodic_utilities'], # F05
      '05' => ['notice_contract_utilities'], # F06
      '07' => ['notice_qualification_utilities'], # F22
      '12' => ['notice_design_cont'], # F13
      '24' => ['notice_concession'], # F25
      '25' => ['notice_concession_award'], # F23
    }

    path = File.join('output', 'mapping', 'ignore.csv')
    rows = CSV.read(path, headers: true)
    headers = rows[0].headers
    enum = rows.to_enum.with_index

    enumerations = CSV.read(File.join('output', 'mapping', 'enumerations.csv'), headers: true)

    files('output/mapping/{}*.csv').each do |filename|
      basename = File.basename(filename, '.csv')

      if basename != 'MOVE'
        number = File.basename(filename).match(/\A(F\d\d)/)[1]
        text = pdftotext(files("source/TED_forms_templates_R2.0.9/#{number}_*.pdf")[0])
      else
        number = basename
        text = ''
      end

      mapped = CSV.read(filename, headers: true).map{ |row| row['label-key'] }
      mapped += enumerations.select{ |row| row['numbers'][number] }.map{ |row| row['label-key'] }
      mapped += ignore.fetch(number, [])
      mapped << '_or'

      minimum_indices = Hash.new(-1)
      label_keys(text).each do |label_key|
        if !mapped.include?(label_key)
          index = enum.find_index do |row, i|
            row['label-key'] == label_key && i > minimum_indices[label_key]
          end
          if index
            if rows[index]['numbers'] && !rows[index]['numbers'][number]
              rows[index]['numbers'] << "|#{number}"
            end
          end
        end
      end
    end

    CSV.open(path, 'w') do |csv|
      csv << headers
      rows.each do |row|
        # Sort numbers for consistent output.
        row['numbers'] = row['numbers'].split('|').sort.join('|')
        csv << row
      end
    end
  end

  desc 'Copy label keys, indices and OCDS guidance across forms'
  task :copy do
    source_number = ENV['SOURCE']
    source = files("output/mapping/#{source_number}_*.csv")[0]

    xpaths = {}
    CSV.foreach(source, headers: true) do |row|
      xpaths[row['xpath']] = row
    end

    filenames = files('output/mapping/{}*.csv') - [source]
    filenames.each do |filename|
      headers = nil
      rows = []

      CSV.foreach(filename, headers: true) do |row|
        headers = row.headers
        basename = File.basename(filename, '.csv')

        if basename != 'MOVE'
          target_number = basename.match(/\A(F\d\d)/)[1]
          template = files("source/TED_forms_templates_R2.0.9/#{target_number}_*.pdf")[0]
          text = pdftotext(template)
        else
          text = ''
        end

        label_keys = label_keys(text)
        indices = indices(text)

        key = row['xpath']
        other = xpaths[key]
        if other
          if row['label-key'].nil? && label_keys.include?(other['label-key']) || basename == 'MOVE'
            row['label-key'] = other['label-key']
          end
          if row['index'].nil? && indices.include?(other['index']) || basename == 'MOVE'
            row['index'] = other['index']
          end

          row['comment'] = other['comment']

          guidance = other['guidance']
          if guidance
            row['guidance'] = guidance
          else
            row['guidance'] = "*Pending guidance from #{source_number}*"
          end
        end
        rows << row
      end

      CSV.open(filename, 'w') do |csv|
        csv << headers
        rows.each do |row|
          csv << row
        end
      end
    end
  end

  desc 'Report any incoherences in mappings across forms'
  task :coherence do
    mappings = {}

    files('output/mapping/{}*.csv').each do |filename|
      CSV.foreach(filename, headers: true) do |row|
        if row['label-key']
          # Exception for label:copy command.
          if row['guidance'] && row['guidance'][/\A\*Pending guidance from [FT]\d\d\*\z/]
            row['guidance'] = nil
          end

          key = row['xpath']
          actual = row.fields[1..-1]
          if mappings.key?(key)
            mapping = mappings[key]
            expected = mapping[:value]
            if expected != actual
              message = "#{filename} (#{mapping[:filename]})"
              added = actual - expected
              if added.any?
                message << " added; #{added}"
              end
              removed = expected - actual
              if removed.any?
                message << " removed: #{removed}"
              end
              puts message
            end
          else
            mappings[key] = {filename: filename, value: actual}
          end
        end
      end
    end
  end

  desc 'Reverse-engineer the label keys for transport forms'
  task :reverse do
    FileUtils.mkdir_p('output/labels')

    ignore_labels = [
      # First header
      'enotices.ted.europa.eu',
      # Footnotes
      '1', '2', '3', '4',
      # Right margin
      'PDF T01 EN 2018-10-02 12:12',
      'PDF T02 EN 2018-10-02 12:38',
      # Footer
      'EN Standard form T01 – 1370/07 – Art 7(2) – Prior information notice for public service contract',
      'EN Standard form T02 – 1370/07 – Art 7(3) – Information notice for award of public service contract',
    ]

    label_fixes = {
      'Bus transport services (urban/regional)' => 'Bus transport services (urban/regional) ', # extra space
      'Direct awards' => 'Direct award', # "modified to singular"
      # Multiple labels (T01).
      'Name and addresses (please identify all competent authorities responsible for this procedure)' => ['Name and addresses', 'please identify all competent authorities responsible for this procedure'],
      'Type of contract Services' => ['Type of contract', 'Services'],
      'or Duration in days' => ['or', 'Duration in days'],
      # Multiple labels (T02).
      'yes  no' => ['yes', 'no'],
      'Exclusive rights are granted  yes  no' => ['Exclusive rights are granted', 'yes', 'no'],
      'Social standards (transfer of staff under Dir. 2001/23/EC)' => ['Social standards', 'transfer of staff under Dir. 2001/23/EC'],
      'Description (choose at least one)' => ['Description', 'choose at least one'],
      'Information on value of the contract (excluding VAT)' => ['Information on value of the contract', 'excluding VAT'],
    }

    label_keys = {}
    CSV.read(TableBuilder::FORM_LABELS_CSV_PATH, headers: true).each do |row|
      if row.fields.any?
        label_keys[row['EN']] = row['Label']
      end
    end

    files('source/English/EN_T{}.pdf').each do |filename|
      basename = File.basename(filename, '.pdf')

      text = `pdftotext #{filename} -`.
        # Put long strings onto one line.
        gsub(/\n([a-z])(?!f applicable)/, ' \1').
        # Ignore non-label keys.
        gsub(/ [1-4]\b(, [1-4]\b)*/, ''). # reference
        gsub("\u20de", ''). # check box
        gsub("◯", ''). # radio button
        gsub(/\[\s+\]| \. /, ''). # code data entry
        gsub('/  /', ''). # date data entry
        gsub(/\bT-\d\d\b/, ''). # code
        gsub(/%$/, '') # percentage

      strings = text.each_line.flat_map do |line|
        if line[/:\s/]
          line.split(':')
        else
          line
        end
      end

      labels = strings.flat_map do |string|
        # Remove indices.
        label = string.sub(/\b[IV]+(\.\d+)+\) /, '').strip

        if !label.empty? && !ignore_labels.include?(label)
          # Remove parentheses.
          if label[0] == '(' && label[-1] == ')'
            label = label[1..-2]
          end

          label_fixes.fetch(label, label)
        else
          []
        end
      end

      success = []
      failure = []
      labels.each do |label|
        if label_keys.include?(label)
          success << label_keys[label]
        else
          failure << label
        end
      end

      failure.each do |label|
        puts "unexpected label: #{label}"
      end

      File.open("output/labels/#{basename}.csv", 'w') do |f|
        f.write success.join("\n")
      end
    end
  end
end
