namespace :label do
  desc 'Create or update files for mapping XPath values to corresponding label keys'
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
      Nokogiri::XML(File.read(filename)).xpath("/#{basename}//*|/#{basename}//@*").each do |element|
        xpath = element.path.sub(/\A\/F.._2014/, '').gsub(/\[\d+\]/, '').gsub(%r{\b(?:choice|group|sequence)/}, '')
        # Exclude XSD elements, paragraph tags, form identifier, and attributes for empty elements.
        if !%w(choice group sequence P @FORM @CODE @TYPE @VALUE).include?(xpath.split('/')[-1])
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
    files('output/mapping/F{}_*.csv').each do |filename|
      CSV.foreach(filename, headers: true) do |row|
        if row.size != 5
          raise "#{filename}: #{row['xpath']} unquoted comma!"
        end
      end
    end
  end

  desc 'Report any XPath values without corresponding label keys, and vice versa'
  task :missing do
    label_keys_seen = Set.new
    indices_seen = Set.new

    %w(ignore.csv enumerations.csv additional.csv).each do |basename|
      CSV.read(File.join('output', 'mapping', basename), headers: true).each do |row|
        label_keys_seen << row['label-key']
        indices_seen << row['index']
      end
    end

    files('output/mapping/F{}_*.csv').each do |filename|
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

    regex = /\A(annex_d\d|section_\d|directive_201424|directive_201425|#{form_title_labels.join('|')})\z/

    files('source/*_TED_forms_templates/F{}_*.pdf').each do |filename|
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
    files('output/mapping/F{}_*.csv').each do |filename|
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

    files('output/mapping/F{}_*.csv').each do |filename|
      number = File.basename(filename).match(/\AF(\d\d)/)[1]

      mapped = CSV.read(filename, headers: true).map{ |row| row['label-key'] }
      if ignore.key?(number)
        mapped += ignore[number]
      end
      mapped << '_or'

      text = pdftotext(files("source/*_TED_forms_templates/F#{number}_*.pdf")[0])
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
        csv << row
      end
    end
  end

  desc 'Copy label keys, indices and OCDS guidance across forms'
  task :copy do
    source_number = ENV['SOURCE']
    source = files("output/mapping/F#{source_number}_*.csv")[0]

    xpaths = {}
    CSV.foreach(source, headers: true) do |row|
      xpaths[row['xpath']] = row
    end

    filenames = files('output/mapping/F{}_*.csv') - [source]
    filenames.each do |filename|
      headers = nil
      rows = []

      CSV.foreach(filename, headers: true) do |row|
        headers = row.headers
        target_number = File.basename(filename).match(/\AF(\d\d)/)[1]

        template = files("source/*_TED_forms_templates/F#{target_number}_*.pdf")[0]
        text = pdftotext(template)
        label_keys = label_keys(text)
        indices = indices(text)

        key = row['xpath']
        other = xpaths[key]
        if other
          if row['label-key'].nil? && label_keys.include?(other['label-key'])
            row['label-key'] = other['label-key']
          end
          if row['index'].nil? && indices.include?(other['index'])
            row['index'] = other['index']
          end

          row['comment'] = other['comment']

          guidance = other['guidance']
          if guidance
            row['guidance'] = guidance
          else
            row['guidance'] = "*Pending guidance from F#{source_number}*"
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

    files('output/mapping/F{}_*.csv').each do |filename|
      CSV.foreach(filename, headers: true) do |row|
        if row['label-key']
          # Exception for label:copy command.
          if row['guidance'] && row['guidance'][/\A\*Pending guidance from F\d\d\*\z/]
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
end
