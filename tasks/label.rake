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
        component = xpath.split('/')[-1]
        if !%w(choice group sequence P @CODE @CTYPE @FORM @PUBLICATION @TYPE @VALUE).include?(component)
          xpaths << xpath
        end
        # The PUBLICATION attribute has corresponding form elements on F06.
        if basename[0..2] == 'F06' && component == '@PUBLICATION'
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
        if row['guidance'].nil? && row['comment'] && !row['comment'].start_with?('https://')
          raise "#{filename}: #{row['xpath']} short row!"
        end
        if row.size != 5
          raise "#{filename}: #{row['xpath']} unquoted comma!"
        end
      end
    end
  end

  desc 'Report any XPath values without corresponding label keys, and vice versa'
  task :missing do
    form_title_labels = [
      'notice_contract_award', # F03
      'notice_contract_award_sub', # F03
      'notice_award_utilities', # F06
      'notice_contract_award_sub', # F06
      'notice_relates_to', # F08
      'notice_result_design_cont', # F13
      'notice_corrigendum', # F14
      'notice_corrigendum_sub', # F14
      'notice_mod', # F20
      'notice_mod_sub', # F20
      'notice_social_public', # F21
      'notice_social_util', # F22
      'notice_social_concess', # F23
      'notice_pubservice_pin', # T01
      'notice_pubservice_pin_expl', # T01
      'notice_pubservice_award', # T02
      'notice_pubservice_award_expl', # T02
    ]

    regex = /\A(annex_d\d|section_\d|directive_(?:200981|201423|201424|201425)|#{form_title_labels.join('|')})\z/

    label_keys_seen = Set.new(['_or'])
    indices_seen = Set.new

    %w(additional.csv enumerations.csv ignore.csv omit.csv).each do |basename|
      CSV.read(File.join('output', 'mapping', 'shared', basename), headers: true).each do |row|
        label_keys_seen << row['label-key']
        indices_seen << row['index']
      end
    end

    files('output/mapping/{}*.csv').each do |filename|
      basename = File.basename(filename, '.csv')

      data = CSV.read(filename, headers: true)

      if basename == 'MOVE'
        next if ENV['FORM'].nil?
        number = ENV.fetch('FORM')
        data = select_move_rows(data, number)
      end

      data.each do |row|
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

      if basename == 'MOVE'
        labels = CSV.read("output/labels/EN_#{number}.csv").flatten
        indices = CSV.read("output/indices/EN_#{number}.csv").flatten

        # Identical to below.
        difference = Set.new(labels.reject{ |key| help_text?(key) || key[regex] }) - label_keys_seen
        if difference.any?
          puts "#{basename}: #{difference.to_a.join(', ')}"
        end

        difference = Set.new(indices) - indices_seen
        if difference.any?
          puts "#{basename}: #{difference.to_a.join(', ')}"
        end
      end
    end

    files('source/TED_forms_templates_R2.0.9/{}*.pdf').each do |filename|
      basename = File.basename(filename)

      text = pdftotext(filename)
      labels = label_keys(text)
      indices = indices(text)

      difference = Set.new(labels.reject{ |key| help_text?(key) || key[regex] }) - label_keys_seen
      if difference.any?
        puts "#{basename}: #{difference.to_a.join(', ')}"
      end

      difference = Set.new(indices) - indices_seen
      if difference.any?
        puts "#{basename}: #{difference.to_a.join(', ')}"
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
    # Some form titles are used on later forms, but shouldn't be ignored on their original form. Some legal bases are
    # omitted on some and ignored on others. "Conditions related to the contract" is III.2 except on T02.
    ignore = {
      'F01' => ['notice_pin', 'directive_201424', 'conditions_contract'], # F02 F08 F21 F23
      'F02' => ['notice_contract', 'directive_201424', 'conditions_contract'], # F03 F21 F22
      'F03' => ['directive_201424'],
      'F04' => ['notice_periodic_utilities', 'directive_201425', 'conditions_contract'], # F05
      'F05' => ['notice_contract_utilities', 'directive_201425', 'conditions_contract'], # F06
      'F06' => ['directive_201425'],
      'F07' => ['notice_qualification_utilities', 'directive_201425', 'conditions_contract'], # F22
      'F08' => ['notice_buyer_profile', 'notice_pin', 'directive_201424', 'directive_201425'], # F02 F05 F21 F22
      'F12' => ['notice_design_cont', 'directive_201424', 'directive_201425', 'conditions_contract'], # F13
      'F13' => ['directive_201424', 'directive_201425'],
      'F14' => ['directive_201423', 'directive_201424', 'directive_201425'],
      'F20' => ['directive_201423', 'directive_201424', 'directive_201425'],
      'F21' => ['directive_201424', 'conditions_contract'],
      'F22' => ['directive_201425', 'conditions_contract'],
      'F24' => ['notice_concession', 'directive_201423'], # F25
      'F25' => ['notice_concession_award'], # F23
    }

    path = File.join('output', 'mapping', 'shared', 'ignore.csv')
    rows = CSV.read(path, headers: true)
    headers = rows[0].headers
    enum = rows.to_enum.with_index

    enumerations = CSV.read(File.join('output', 'mapping', 'shared', 'enumerations.csv'), headers: true)

    files('output/mapping/{}*.csv').each do |filename|
      basename = File.basename(filename, '.csv')

      if basename == 'MOVE'
        next if ENV['FORM'].nil?
        number = ENV.fetch('FORM')
        labels = CSV.read("output/labels/EN_#{number}.csv").flatten
      else
        number = basename.match(/\A(F\d\d)/)[1]
        next if %w(F16 F17 F18 F19).include?(number)
        labels = label_keys(pdftotext(files("source/TED_forms_templates_R2.0.9/#{number}_*.pdf")[0]))
      end

      mapped = CSV.read(filename, headers: true).map{ |row| row['label-key'] }
      mapped += enumerations.select{ |row| row['numbers'][number] }.map{ |row| row['label-key'] }
      mapped += ignore.fetch(number, [])
      mapped << '_or'

      minimum_indices = Hash.new(-1)
      labels.each do |label_key|
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

      basename = File.basename(filename, '.csv')

      if basename == 'MOVE'
        text = ''
      else
        number = basename.match(/\A(F\d\d)/)[1]
        next if %w(F16 F17 F18 F19).include?(number)
        text = pdftotext(files("source/TED_forms_templates_R2.0.9/#{number}_*.pdf")[0])
      end

      label_keys = label_keys(text)
      indices = indices(text)

      CSV.foreach(filename, headers: true) do |row|
        headers = row.headers

        key = row['xpath']
        other = xpaths[key]
        if other
          if row['label-key'].nil? && (label_keys.include?(other['label-key']) || basename == 'MOVE')
            row['label-key'] = other['label-key']
          end
          if row['index'].nil? && (indices.include?(other['index']) || basename == 'MOVE')
            row['index'] = other['index']
          end

          row['comment'] = other['comment']

          guidance = other['guidance']
          if guidance
            row['guidance'] = guidance
          else
            row['guidance'] = "*Waiting for mapping from #{source_number}*"
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

  desc 'Report any inconsistencies in mappings across forms'
  task :consistent do
    mappings = {}

    files('output/mapping/{}*.csv').each do |filename|
      if ENV['INCLUDE_LABEL_KEY']
        index = 1
      elsif ENV['INCLUDE_INDEX']
        index = 2
      else
        index = 3
      end
      CSV.foreach(filename, headers: true) do |row|
        if row['label-key']
          # Exception for label:copy command.
          if row['guidance'] && row['guidance'][/\A\*Waiting for mapping from [FT]\d\d\*\z/]
            row['guidance'] = nil
          end

          key = row['xpath']
          actual = row.fields[index..-1]
          if mappings.key?(key)
            mapping = mappings[key]
            expected = mapping[:value]
            if expected != actual
              message = "#{filename.ljust(27)} (#{mapping[:filename].ljust(27)}) #{row[0]}"
              added = actual - expected
              if added.any?
                message << "\nadded: #{added}"
              end
              removed = expected - actual
              if removed.any?
                message << "\nremoved: #{removed}"
              end
              puts "#{message}\n\n"
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
    FileUtils.mkdir_p('output/indices')

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
      'Bus transport services (urban/regional)' => ['Bus transport services (urban/regional) '], # extra space
      'Direct awards' => ['Direct award'], # "modified to singular"
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

      labels = []
      indices = []

      strings.each do |label|
        pattern = /\b([IV]+(?:\.\d+)+)\) /
        if label[pattern]
          # Collect and remove indices.
          indices << $1
          label.sub!(pattern, '')
        end

        label.strip!

        if !label.empty? && !ignore_labels.include?(label)
          if label[0] == '(' && label[-1] == ')'
            label = label[1..-2]
          end
          labels += label_fixes.fetch(label, [label])
        end
      end

      success = []
      failure = []
      labels.each do |label|
        if label_keys.include?(label)
          label_key = label_keys[label]
          if !label_key[/\AH_foot_\d\z/]
            success << label_key
          end
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

      File.open("output/indices/#{basename}.csv", 'w') do |f|
        f.write indices.join("\n")
      end
    end
  end
end
