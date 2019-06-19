# This file is abandoned, because the labels spreadsheet doesn't have labels for all relevant XML elements.

=begin
# http://publications.europa.eu/mdr/eprocurement/ted/index.html
curl -O http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/publication/XML_Labels_Mapping_R209.zip
unzip XML_Labels_Mapping_R209.zip
rm -f XML_Labels_Mapping_R209.zip

in2csv --write-sheets - "source/XML Labels mapping R2.09.xlsx" > /dev/null
=end

LABEL_IGNORE_COMMON = [
  'cost',
  'currencies',
  'empty',
  'no_doc_ext',
  'phone',
  'string_20',
  'string_50',
  'string_100',
  'string_200',
  'string_300',
  'string_400',
  't_ce_language_list',
  'time',
  'url',

  'date', # date_full
  'integer', # nb_contract, etc.
  'non-empty', # anything but empty
  'text_200', # text_ft_single_line
  'textarea_200', # text_ft_multi_lines
  'textarea_400', # text_ft_multi_lines
  'textarea_1000', # text_ft_multi_lines
  'textarea_1500', # text_ft_multi_lines
  'textarea_2500', # text_ft_multi_lines
  'textarea_4000', # text_ft_multi_lines
]

LABEL_IGNORE_XSD = [
  'cpv_code.xsd', # cpv_codes.xsd
  'cpv_supplementary_code.xsd', # cpv_supplementary_codes.xsd
  'languages.xsd',
  'nuts_codes.xsd', # nuts_codes_2016.xsd
]

LABEL_FIXES = {
  0 => {
    'S2-01-03' => 'TYPE_CONTRACT',
    'S2-02-07' => 'time_frame',
    'S2-02-13' => 'eu_union_funds',
    'S4-01-03' => 'dps_purchasers',
    'S4-01-06' => 'eauction',
    'S4-01-08' => 'gpa',
    'S4-02-02' => 'receipt_tenders',
  }
}

namespace :legacy do
  desc 'Add labels to XML elements'
  task :label do
    subexpression = (LABEL_IGNORE_COMMON + LABEL_FIXES.flat_map{ |_, fixes| fixes.values } + ['ADDR-S1', 'ADDR-S5', 'ADDR-S6']).join('|')

    configuration = {
      'XML element name' => {
        sanitizer: ->(string) {
          # Normalize whitespace.
          string.gsub(/\|(?! )/, '| ').gsub(' =', '=').sub(' ]', ']').sub('@ ', '@').sub(' @', '@').
          # Correct syntax.
          gsub('/[@', '[@').sub(/\/(@[A-Z_]+="[^"]+")/, '[\1]')
        },
        matcher: %r{
          \A(?:
            ([A-Z_]+)|                                                             # NAME
            ([A-Z_]+/[A-Z_]+)|                                                     # NAME/NAME
            ([A-Z_]+/@[A-Z_]+)(?:\n([A-Z_]+/@[A-Z_]+))*|                           # NAME/@ATTR\n…
            ([A-Z_]+\[@[A-Z_]+="[^"]+"\])(?:\n\|\s([A-Z_]+\[@[A-Z_]+="[^"]+"\]))*| # NAME[@ATTR="VALUE"]\n| …
            ([A-Z0-9_]+\[@[A-Z_]+="[^"]+"(?:,@[A-Z_]+="[^"]+")*\]/@[A-Z_]+)|       # NAME[@ATTR="VALUE",@ATTR="VALUE"]/@ATTR
            ([A-Z_]+)\n([A-Z_]+)|                                                  # NAME\n…
            ([A-Z_]+)(?:\n\|\s([A-Z_]+))+|                                         # NAME\n| …
            \(\s([A-Z_]+),\s([A-Z_]+)\s\|\s([A-Z_]+)\s\)\n\|\s([A-Z_]+)            # ( NAME, NAME | NAME )\n| NAME
          )\z
        }x,
      },
      'Type / Value range' => {
        sanitizer: ->(string) {
          # Normalize whitespace.
          string.gsub(/\|(?! )/, '| ').gsub(/(?<!\n)\|/, "\n|").sub('non- empty', 'non-empty')
        },
        matcher: %r{
          \A(?:
            ([A-Z_]+)|                                                             # NAME
            ([A-Z_]+)\n([A-Z_]+)|                                                  # NAME\nNAME
            ([A-Z_]+)(?:\n\|\s([A-Z_]+))*|                                         # NAME\n| NAME …
            (#{subexpression})(?:\n(#{subexpression}))*|                           # name\nname
            value\srange\s+in\s([a-z_]+)|                                          # value range in name
            value\srange\s+in\s[a-z_]+\.xsd                                        # value range in name.xsd
          )\z
        }x,
        logger: ->(value) { !value[/\Avalue range +in [a-z_]+\.xsd\z/] },
        excluded: LABEL_IGNORE_COMMON + LABEL_IGNORE_XSD,
      },
    }

    files('output/summaries/{}_*.csv').each do |output|
      label_key_to_label = {}
      CSV.read('source/XML Labels mapping R2.09_7.csv', headers: true).each do |row|
        label_key_to_label[row['Label']] = row['EN']
      end

      number = Integer(File.basename(output, '.csv').gsub(/\AF0?|_2014\z/, '')) - 1
      source = "source/XML Labels mapping R2.09_#{number}.csv"

      if File.exist?(source)
        # Map values from 'XML element name' and 'Type / Value range' to rows.
        xml_name_to_label_row = {}
        CSV.read(source, headers: true).each do |row|
          fix = LABEL_FIXES[number][row['Field ID']]
          if fix
            if fix[/[a-z]/]
              field = 'Type / Value range'
            else
              field = 'XML element name'
            end
            value = row[field]
            if value.nil?
              row[field] = fix
            else
              $stderr.puts "Field ID '#{row['Field ID']}' has '#{value}' for #{field}, not setting to '#{fix}'"
            end
          end

          xml_names = []

          configuration.each do |field, config|
            value = row[field]
            if value
              values = config[:sanitizer].call(value.strip).scan(config[:matcher]).flatten.compact
              if values.empty? && config.fetch(:logger, ->(value) { true }).call(value)
                $stderr.puts "'#{value}' for #{field} can't be parsed"
              end
              xml_names += values - config.fetch(:excluded, [])
            end
          end

          xml_names.each do |xml_name|
            other = xml_name_to_label_row[xml_name]
            if other
              difference = HashDiff.diff(row.to_h.except('Field ID'), other.to_h.except('Field ID'))
              if difference.any?
                $stderr.puts "'#{xml_name}' matches different rows: #{difference}"
              end
            else
              xml_name_to_label_row[xml_name] = row
            end
          end
        end

        # To do:
        # - Handle NAME/NAME, NAME/@ATTR, NAME[@ATTR="VAL"], NAME[@ATTR="VALUE",@ATTR="VALUE"]/@ATTR in 'XML element name'
        # - Instead of printing, merge into summary CSV
        # - 'Forms validation rules' doesn't have 'Label-key', but has 'Description' and 'Range of values'
        CSV.read(output, headers: true).each do |row|
          xml_name = row['name'] || row['ref']
          label_row = xml_name_to_label_row[xml_name]
          if label_row
            label_keys = label_row['Label-key']
            puts "#{label_row['Description']} (#{xml_name})"
            if label_keys
              label_keys = label_keys.split("\n").map{ |label_key| label_key_to_label.fetch(label_key.sub(/\A</, '')) }
              if label_keys[0] == label_row['Description']
                label_keys.shift
              end
              if label_keys.any?
                puts "  #{label_keys.join("\n  ")}"
              end
            else
              puts "  no label keys"
            end
            puts
          else
            $stderr.puts "'#{xml_name}' has no label"
          end
        end
      end
    end
  end
end
