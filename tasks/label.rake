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

    # Some form titles are used on later forms and therefore ignored with ignore.csv.
    form_title_labels = [
      # notice_pin on F02
      # notice_contract on F03
      'notice_contract_award', # F03
      'notice_contract_award_sub', # F03
      # notice_periodic_utilities on F05
      # notice_contract_utilities on F06
      'notice_award_utilities', # F06
      'notice_contract_award_sub', # F06
      # notice_qualification_utilities on F22
      'notice_relates_to', # F08
      # notice_design_cont on F13
      'notice_result_design_cont', # F13
      'notice_corrigendum', # F14
      'notice_mod', # F20
      'notice_social_public', # F21
      'notice_social_util', # F22
      'notice_social_concess', # F23
      # notice_concession on F24
      # notice_concession_award on F23
    ]

    regex = /\A(annex_d\d|section_\d|directive_201424|#{form_title_labels.join('|')})\z/

    files('source/*_TED_forms_templates/F{}_*.pdf').each do |filename|
      text = pdftotext(filename)

      difference = Set.new(label_keys(text).reject{ |key| help_text?(key) || key[regex] }) - label_keys_seen
      if difference.any?
        puts "#{File.basename(filename)}: #{difference.to_a.join(', ')}"
      end

      difference = Set.new(text.scan(/\b[IV]+(?:\.\d+)*/).flatten) - indices_seen
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

  desc 'Copy OCDS guidance across forms'
  task :copy do
    number = ENV['SOURCE']
    source = Dir["output/mapping/F#{number}_*.csv"][0]

    xpaths = {}
    CSV.foreach(source, headers: true) do |row|
      xpaths[row['xpath']] = row
    end

    files('output/mapping/F{}_*.csv').each do |filename|
      headers = nil
      rows = []

      CSV.foreach(filename, headers: true) do |row|
        headers = row.headers

        key = row['xpath']
        other = xpaths[key]
        if other
          row['comment'] = other['comment']

          guidance = other['guidance']
          if guidance
            row['guidance'] = guidance
          else
            row['guidance'] = "*Pending guidance from F#{number}*"
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
