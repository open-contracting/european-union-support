desc 'Build a table with guidance'
task :table do
  def help_labels(labels)
    index = labels.index{ |key| !help_text?(key) } || 1
    help_labels = labels[0...index]
    labels.replace(labels[index..-1])
    help_labels
  end

  ignore_csv = CSV.read('output/mapping/ignore.csv', headers: true)
  enumerations_csv = CSV.read('output/mapping/enumerations.csv', headers: true)

  files('output/mapping/F{}_*.csv').each do |filename|
    number = File.basename(filename).match(/\AF(\d+)/)[1]

    ### Setup

    ignore = ignore_csv.select{ |row| row['numbers'][number] }
    enumerations = enumerations_csv.select{ |row| row['numbers'][number] }

    ignore_seen = Set.new
    enumerations_seen = Set.new

    data = CSV.read(filename, headers: true)
    data_seen = Set.new

    data_skipped = data.take_while{ |row| row['label-key'].nil? } # TODO
    data = data.drop_while{ |row| row['label-key'].nil? }

    # Skip "Supplement to the Official Journal of the European Union" and "Info and online forms".
    labels = label_keys(pdftotext(Dir["source/*_TED_forms_templates/F#{number}_*.pdf"][0]))[2..-1]

    ### Build

    builder = TableBuilder.new(ENV['LANGUAGE'] || 'EN')

    builder.heading(number, labels.shift)

    if number == '03'
      # Skip "Results of the procurement procedure".
      labels.shift
    end
    # Skip "Directive 2014/24/EU".
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

      # The form may change the order of XML elements.
      elsif i = data[0..14].index{ |row| row['label-key'] == key }
        data_seen << key
        row = data.delete_at(i)

        data_skipped += data.take_while{ |row| row['label-key'].nil? }
        data = data.drop_while{ |row| row['label-key'].nil? }

        builder.row(key, help_labels: help_labels(labels), xpath: row['xpath'], index: row['index'], guidance: '')

      elsif ignore_seen.include?(key)
        builder.row(key, help_labels: help_labels(labels))

      elsif enumerations_seen.include?(key)
        builder.row(key, help_labels: help_labels(labels), reference: true)

      elsif data_seen.include?(key)
        builder.row(key, help_labels: help_labels(labels), reference: true)

      else
        p data
        raise "unexpected key '#{key}'"
      end
    end

    builder.end_table

    if ignore.any?
      $stderr.puts ignore
    end
    if enumerations.any?
      $stderr.puts enumerations
    end

    puts "# Standard forms for public procurement\n\n"
    puts builder
  end
end
