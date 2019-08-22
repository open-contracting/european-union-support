HELP_TEXT = {
  'F08' => %w(directive_201424 directive_201425 directive_200981),
}

# If the label keys appear after "One of the following:".
CONDITIONAL_HELP_TEXT = {
  'F02' => %w(notice_pin notice_buyer_profile),
  'F03' => %w(notice_contract notice_ex_ante),
  'F05' => %w(notice_periodic_utilities notice_buyer_profile),
  'F06' => %w(notice_contract_utilities notice_ex_ante),
  'F21' => %w(notice_pin notice_buyer_profile notice_contract notice_ex_ante),
  'F22' => %w(notice_periodic_indicative notice_buyer_profile notice_qualification_utilities notice_contract notice_ex_ante),
  'F23' => %w(notice_pin notice_ex_ante),
  'F25' => %w(notice_concession notice_ex_ante),
}

KNOWN_SKIPPED_XPATHS = %w(/@LG /@CATEGORY)

desc 'Build a table with guidance'
task :table do
  def swap(labels, label_1, label_2, reverse: false)
    if reverse
      meth = :rindex
    else
      meth = :index
    end
    index_1 = labels.send(meth, label_1)
    index_2 = labels.send(meth, label_2)
    if index_1 && index_2
      labels[index_1] = label_2
      labels[index_2] = label_1
    end
  end

  def help_labels(labels, number: nil)
    if labels[0] == 'H_one_following'
      override = CONDITIONAL_HELP_TEXT.fetch(number, [])
    else
      override = HELP_TEXT.fetch(number, [])
    end

    index = labels.index{ |key| !help_text?(key, number: number, override: override) } || 1
    help_labels = labels[0...index]
    labels.replace(labels[index..-1] || [])
    help_labels
  end

  def report(rows, message)
    if rows.any?
      $stderr.puts "#{rows.size} #{message}"
      $stderr.puts rows
      $stderr.puts
    end
  end

  omit_csv = CSV.read('output/mapping/shared/omit.csv', headers: true)
  ignore_csv = CSV.read('output/mapping/shared/ignore.csv', headers: true)
  enumerations_csv = CSV.read('output/mapping/shared/enumerations.csv', headers: true)
  additional_csv = CSV.read('output/mapping/shared/additional.csv', headers: true)

  # Some forms have elements before Section 1.
  has_header = %w(F01 F04 F07 F08 F12 F13 F15 F20 F21 F22 F23)

  files('output/mapping/{}*.csv').each do |filename|
    basename = File.basename(filename, '.csv').sub('_2014', '')

    if basename == 'MOVE'
      number = ENV.fetch('FORM')
      labels = CSV.read("output/labels/EN_#{number}.csv").flatten
      extra_xpaths_to_list = {}
    else
      number = basename.match(/\A(F\d\d)/)[1]
      labels = label_keys(pdftotext(Dir["source/TED_forms_templates_R2.0.9/#{number}_*.pdf"][0]))
      extra_xpaths_to_list = {
        # A single `currency` label stands for 2-3 elements.
        '/OBJECT_CONTRACT/VAL_TOTAL/@CURRENCY' => [
          '/OBJECT_CONTRACT/VAL_RANGE_TOTAL/@CURRENCY',
        ],
        '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_ESTIMATED_TOTAL/@CURRENCY' => [
          '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_TOTAL/@CURRENCY',
          '/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_RANGE_TOTAL/@CURRENCY',
        ],
      }
      if %w(F23 F25).include?(number)
        extra_xpaths_to_list['/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_ESTIMATED_TOTAL/@CURRENCY'].pop
      end
    end

    extra_xpaths_to_skip = extra_xpaths_to_list.values.flatten

    # Skip "Supplement to the Official Journal of the European Union" (HD_ojs_) and "Info and online forms" (HD_info_forms).
    labels = labels[2..-1]

    skipper = ->(row) do
      row['label-key'].nil? || extra_xpaths_to_skip.include?(row['xpath'])
    end

    ### Setup

    seen = {
      enumerations: Set.new,
      filename => Set.new,
    }

    omit = omit_csv.select{ |row| row['numbers'][number] }
    ignore = ignore_csv.select{ |row| row['numbers'][number] }
    enumerations = enumerations_csv.select{ |row| row['numbers'][number] }
    additional = additional_csv.select{ |row| row['numbers'][number] }
    data = CSV.read(filename, headers: true)

    if basename == 'MOVE'
      data = select_move_rows(data, number)
    end

    data_skipped = data.take_while(&skipper).reject{ |row| KNOWN_SKIPPED_XPATHS.include?(row['xpath']) }
    data = data.drop_while(&skipper)

    # Swap the order of labels.
    if basename != 'MOVE'
      swap(labels, 'maintype_natagency', 'maintype_localagency')
      swap(labels, 'maintype_localauth', 'maintype_publicbody')
      swap(labels, 'maintype_localauth', 'maintype_localagency')
      swap(labels, 'mainactiv_health', 'other_activity')
      swap(labels, 'mainactiv_postal', 'other_activity', reverse: true)
    end

    ### Build

    builder = TableBuilder.new(ENV['LANGUAGE'] || 'EN', extra_xpaths_to_list)

    # Shift `notice_pin`, `notice_contract`, `notice_contract_award`, etc.
    builder.heading(number, labels.shift)

    builder.add(File.read("output/content/#{number}.md") + "\n")

    if has_header.include?(number)
      builder.table
    end

    while labels.any?
      key = labels.shift

      if key[/\A(annex_d\d|section_\d)\z/]
        if has_header.include?(number) || $1 != 'section_1'
          builder.end_table
        end
        builder.subheading(key)
        builder.table

      elsif key == '_or'
        builder.row(key)

      elsif ignore.any? && ignore[0]['label-key'] == key
        row = ignore.shift
        builder.row(key, help_labels: help_labels(labels, number: number), index: row['index'])

      # Fields appear in a different order in the form and XSD.
      elsif (i = data[0..5].index{ |row| row['label-key'] == key }) && (key != 'weighting' || i == 0)
        row = data.delete_at(i)
        builder.row(key, help_labels: help_labels(labels, number: number), xpath: row['xpath'], index: row['index'], guidance: row['guidance'])

        seen[filename] << key

        data.each do |row|
          if skipper.call(row)
            if row['label-key']
              if !extra_xpaths_to_skip.include?(row['xpath'])
                data_skipped << row
              end
            else
              builder.row(nil, xpath: row['xpath'], index: row['index'], guidance: row['guidance'])
            end
          else
            break
          end
        end
        data = data.drop_while(&skipper)

      elsif enumerations.any? && enumerations[0]['label-key'] == key
        row = enumerations.shift
        builder.row(key, help_labels: help_labels(labels, number: number), xpath: row['xpath'], value: row['value'], guidance: row['guidance'])

        seen[:enumerations] << key

      elsif additional.any? && additional[0]['label-key'] == key
        row = additional.shift
        builder.row(key, help_labels: help_labels(labels, number: number), guidance: row['guidance'])

      elsif omit.any? && omit[0]['label-key'] == key
        omit.shift

      elsif seen[:enumerations].include?(key)
        builder.row(key, help_labels: help_labels(labels, number: number), value: :sentinel, reference: true)

      elsif seen[filename].include?(key) && number != 'F14'
        builder.row(key, help_labels: help_labels(labels, number: number), reference: true)

      else
        # Print debug information to help diagnose the issue.
        $stderr.puts "\noutput:"
        $stderr.puts builder
        $stderr.puts "\nunprocessed rows:"
        $stderr.puts data.map(&:to_h)
        $stderr.puts "\nunprocessed labels:"
        $stderr.puts labels.inspect
        $stderr.puts "\nindex of key in data:"
        $stderr.puts data.index{ |row| row['label-key'] == key }
        $stderr.puts "\nomit: #{omit.any? && omit[0]['label-key']}"
        $stderr.puts "ignore: #{ignore.any? && ignore[0]['label-key']}"
        $stderr.puts "enumerations: #{enumerations.any? && enumerations[0]['label-key']}"
        $stderr.puts "additional: #{additional.any? && additional[0]['label-key']}"
        raise "unexpected key: #{key}"
      end
    end

    builder.end_table

    puts builder

    report(omit, 'unprocessed rows from omit.csv')
    report(ignore, 'unprocessed rows from ignore.csv')
    report(enumerations, 'unprocessed rows from enumerations.csv')
    report(additional, 'unprocessed rows from additional.csv')
    report(data, "unprocessed rows from #{basename}")
    report(data_skipped, "skipped rows from #{basename}")
  end
end
