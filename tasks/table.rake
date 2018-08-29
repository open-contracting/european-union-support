desc 'Build a table with guidance'
task :table do
  def swap(labels, label_1, label_2)
    index_1 = labels.index(label_1)
    index_2 = labels.index(label_2)
    labels[index_1] = label_2
    labels[index_2] = label_1
  end

  def help_labels(labels)
    index = labels.index{ |key| !help_text?(key) } || 1
    help_labels = labels[0...index]
    labels.replace(labels[index..-1])
    help_labels
  end

  def report(rows, message)
    if rows.any?
      $stderr.puts message
      $stderr.puts rows
      $stderr.puts
    end
  end

  ignore_csv = CSV.read('output/mapping/ignore.csv', headers: true)
  enumerations_csv = CSV.read('output/mapping/enumerations.csv', headers: true)
  additional_csv = CSV.read('output/mapping/additional.csv', headers: true)

  files('output/mapping/F{}_*.csv').each do |filename|
    basename = File.basename(filename)
    number = basename.match(/\AF(\d+)/)[1]

    skipper = ->(row) do
      row['label-key'].nil? ||
      # A single `currency` label stands for 2-3 elements.
      # `/F03_2014/OBJECT_CONTRACT/VAL_TOTAL/@CURRENCY`
      row['xpath'] == '/OBJECT_CONTRACT/VAL_RANGE_TOTAL/@CURRENCY' ||
      # `/F03_2014/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_TOTAL/@CURRENCY`
      row['xpath'] == '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_ESTIMATED_TOTAL/@CURRENCY' ||
      row['xpath'] == '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/@CURRENCY'
    end

    ### Setup

    seen = {
      enumerations: Set.new,
      filename => Set.new,
    }

    ignore = ignore_csv.select{ |row| row['numbers'][number] }
    enumerations = enumerations_csv.select{ |row| row['numbers'][number] }
    additional = additional_csv.select{ |row| row['numbers'][number] }
    data = CSV.read(filename, headers: true)

    data_skipped = data.take_while(&skipper)
    data = data.drop_while(&skipper)

    # Skip "Supplement to the Official Journal of the European Union" (HD_ojs_) and "Info and online forms" (HD_info_forms).
    labels = label_keys(pdftotext(Dir["source/*_TED_forms_templates/F#{number}_*.pdf"][0]))[2..-1]

    # Swap the order of labels.
    swap(labels, 'maintype_natagency', 'maintype_localagency')
    swap(labels, 'maintype_localauth', 'maintype_publicbody')
    swap(labels, 'maintype_localauth', 'maintype_localagency')
    swap(labels, 'mainactiv_health', 'other_activity')

    ### Build

    builder = TableBuilder.new(ENV['LANGUAGE'] || 'EN')

    # Shift `notice_pin`, `notice_contract`, `notice_contract_award`, etc.
    builder.heading(number, labels.shift)

    if number == '03'
      # Skip "Results of the procurement procedure" (notice_contract_award_sub).
      labels.shift
    end
    # Skip "Directive 2014/24/EU" (directive_201424).
    labels.shift

    if number == '01'
      builder.table
    end

    while labels.any?
      key = labels.shift

      if key[/\A(?:annex_d\d|section_\d)\z/]
        if number != '01' || $0 != 'section_1'
          builder.end_table
        end
        builder.subheading(key)
        builder.table

      elsif ignore.any? && ignore[0]['label-key'] == key
        row = ignore.shift
        builder.row(key, help_labels: help_labels(labels), index: row['index'])

      elsif enumerations.any? && enumerations[0]['label-key'] == key
        row = enumerations.shift
        builder.row(key, help_labels: help_labels(labels), xpath: row['xpath'], value: row['value'], guidance: row['guidance'])

        seen[:enumerations] << key

      # Fields appear in a different order in the form and XSD.
      elsif i = data[0..3].index{ |row| row['label-key'] == key }
        row = data.delete_at(i)
        builder.row(key, help_labels: help_labels(labels), xpath: row['xpath'], index: row['index'], guidance: row['guidance'])

        seen[filename] << key

        data.each do |row|
          if skipper.call(row)
            if row['label-key']
              data_skipped << row
            else
              builder.row(nil, xpath: row['xpath'], index: row['index'], guidance: row['guidance'])
            end
          else
            break
          end
        end
        data = data.drop_while(&skipper)

      elsif additional.any? && additional[0]['label-key'] == key
        row = additional.shift
        builder.row(key, help_labels: help_labels(labels), guidance: row['guidance'])

      elsif seen[:enumerations].include?(key) || seen[filename].include?(key)
        builder.row(key, help_labels: help_labels(labels), reference: true)

      else
        $stderr.puts builder
        $stderr.puts data.map(&:to_h)
        $stderr.puts data.index{ |row| row['label-key'] == key }
        raise "unexpected key '#{key}'"
      end
    end

    builder.end_table

    puts builder

    report(ignore, 'ignore.csv')
    report(enumerations, 'enumerations.csv')
    report(additional, 'additional.csv')
    report(data, basename)
    report(data_skipped, 'skipped')
  end
end
