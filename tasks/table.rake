desc 'Build a table with guidance'
task :table do
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

  files('output/mapping/F{}_*.csv').each do |filename|
    basename = File.basename(filename)
    number = basename.match(/\AF(\d+)/)[1]

    skipper = ->(row) do
      row['label-key'].nil? ||
      # A single `currency` label stands for 2-3 elements.
      # `/F03_2014/OBJECT_CONTRACT/VAL_TOTAL/@CURRENCY`
      row['xpath'] == '/F03_2014/OBJECT_CONTRACT/VAL_RANGE_TOTAL/@CURRENCY' ||
      # `/F03_2014/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_TOTAL/@CURRENCY`
      row['xpath'] == '/F03_2014/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_ESTIMATED_TOTAL/@CURRENCY' ||
      row['xpath'] == '/F03_2014/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/@CURRENCY'
    end

    ### Setup

    ignore = ignore_csv.select{ |row| row['numbers'][number] }
    enumerations = enumerations_csv.select{ |row| row['numbers'][number] }

    ignore_seen = Set.new
    enumerations_seen = Set.new

    data = CSV.read(filename, headers: true)
    data_seen = Set.new

    data_skipped = data.take_while(&skipper)
    data = data.drop_while(&skipper)

    # Skip "Supplement to the Official Journal of the European Union" (HD_ojs_) and "Info and online forms" (HD_info_forms).
    labels = label_keys(pdftotext(Dir["source/*_TED_forms_templates/F#{number}_*.pdf"][0]))[2..-1]

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

    builder.table

    while labels.any?
      key = labels.shift

      if key[/\Asection_\d\z/]
        builder.end_table
        builder.table(key)

      elsif ignore.any? && ignore[0]['label-key'] == key
        ignore_seen << key
        row = ignore.shift

        builder.row(key, help_labels: help_labels(labels), index: row['index'])

      elsif enumerations.any? && enumerations[0]['label-key'] == key
        enumerations_seen << key
        row = enumerations.shift

        builder.row(key, help_labels: help_labels(labels), xpath: row['xpath'], value: row['value'], guidance: '')

      # Fields appear in a different order in the form and XSD.
      elsif i = data[0..3].index{ |row| row['label-key'] == key }
        data_seen << key
        row = data.delete_at(i)

        data_skipped += data.take_while(&skipper)
        data = data.drop_while(&skipper)

        builder.row(key, help_labels: help_labels(labels), xpath: row['xpath'], index: row['index'], guidance: '')

      elsif enumerations_seen.include?(key)
        builder.row(key, help_labels: help_labels(labels), reference: true)

      elsif data_seen.include?(key)
        builder.row(key, help_labels: help_labels(labels), reference: true)

      else
        $stderr.puts builder
        $stderr.puts data.map(&:to_h)
        $stderr.puts data.index{ |row| row['label-key'] == key }
        raise "unexpected key '#{key}'"
      end
    end

    builder.end_table

    puts "# Standard forms for public procurement\n\n"
    puts builder

    report(ignore, 'ignore.csv')
    report(enumerations, 'enumerations.csv')
    report(data, basename)
    report(data_skipped, 'skipped')
  end
end
