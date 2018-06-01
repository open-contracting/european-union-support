require 'csv'
require 'delegate'

require 'active_support/core_ext/hash/except'
require 'hashdiff'
require 'nokogiri'

# The script doesn't check whether all tags of the forms are visited during parsing, instead assuming the TED
# documentation about form structure is correct.

# These known attributes will automatically be added to the built tree.
# `:use` and `:fixed` are unique to `attribute` tags.
ATTRIBUTES   = %i(tag name type ref fixed maxOccurs minOccurs use)
# These attributes are used internally to build a locator for a node in the tree.
LOCATORS     = %i(index0 index1 index2 index3 index4 index5 index6 index7)
RESTRICTIONS = %i(enumeration maxLength maxInclusive minInclusive minExclusive pattern totalDigits)
REFERENCES   = %i(extension restriction reference)
ANNOTATIONS  = %i(unique annotation)

# All attributes that can be assigned.
ASSIGNABLE = ATTRIBUTES + LOCATORS + REFERENCES + ANNOTATIONS + RESTRICTIONS

# All attributes, excluding compressed and predictable attributes.
HEADERS    = ATTRIBUTES + %i(cardinality) + REFERENCES + ANNOTATIONS + RESTRICTIONS - [
  # Attributes
  :fixed, # 31 times: "F##" (FORM), "NO" (PUBLICATION), "MONTH" (TYPE), "QSU_CALL_COMPETITION" (TYPE)
  :maxOccurs, # cardinality
  :minOccurs, # cardinality
  :use, # 140 times: "required" / all but 7 attributes are required (PUBLICATION)

  # Restrictions
  :maxLength, # 11 times: "100" (TOWN) / others implied by :name, :type, :restriction, :extension
  :maxInclusive, # 4 times: "100", "10000"
  :minInclusive, # once: "1"
  :minExclusive, # 8 times: "0"

  # Annotations
  :unique, # once
]

# Avoid expanding common types to keep the CSVs small.
NO_FOLLOW = [
  # base
  'cost',
  'contact',
  'string_with_letter',

  # ref
  'annex_d1_part1',
  'annex_d2_part1',

  # type
  'ac_definition',
  'contact_contracting_body',
  'contact_contractor',
  'contact_review',
  'empty',
  'no_award',
  'phone',
  'text_ft_multi_lines', # see readme
]

# Avoid expanding common bases to keep the CSVs small. Note differences in readme.
NO_CHILDREN = [
  'lefti',
  'complement_info',
]

# Skip enumeration annotations. Note annotations in readme.
NO_ANNOTATIONS = [
  't_currency_tedschema',
  't_legal-basis_tedschema',
]

require_relative 'lib/tree_node'
require_relative 'lib/xml_parser'

def directories
  if ENV['DIRECTORY']
    directories = [ENV['DIRECTORY']]
  else
    directories = Dir[File.join('source', 'TED_*_R2')].sort
  end
end

def forms(directory, extension)
  suffix = "_2014.#{extension}"
  if ENV['FORMS']
    ENV['FORMS'].split(',').map{ |number| File.join(directory, "F#{number}#{suffix}") }
  else
    Dir[File.join(directory, "F*#{suffix}")].sort
  end
end

task :common do
  directories.each do |directory|
    references = Set.new

    # Get the `base`, `ref` and `type` re-used across forms.
    forms(directory, 'xsd').each do |filename|
      parser = XmlParser.new(filename)

      references += parser.schema.xpath('.//*[@ref]').reject{ |n|
        parser.schema.xpath("./xs:#{n.name}[@name='#{n['ref'].split(':', 2).last}']").any?
      }.map{ |n| n['ref'] }

      %w(base type).each do |name|
        references += parser.schema.xpath(".//*[@#{name}]").reject{ |n|
          parser.schema.xpath(%w(complex simple).map{ |prefix| "./xs:#{prefix}Type[@name='#{n[name]}']" }.join('|')).any?
        }.map{ |n| n[name] }
      end
    end

    # The above will not collect the references in NO_FOLLOW.
    references += NO_FOLLOW

    parser = XmlParser.new(File.join(directory, 'common_2014.xsd'))

    ns = parser.node_set(parser.schema.element_children, size: 0..999, names: %w(import include element group complexType simpleType), name_only: true)
    ns.each do |c|
      if references.include?(c['name'])
        parser.elements(c, 0, index0: c['name'], enter: true)
      end
    end

    parser.to_csv
  end
end

task :forms do
  directories.each do |directory|
    forms(directory, 'xsd').each do |filename|
      parser = XmlParser.new(filename, follow: false)

      abbreviation = parser.basename.sub('_2014', '')

      # Navigate to the form's main sequence.
      ns = parser.node_set(parser.schema.xpath("./xs:element[@name='#{parser.basename}']"), size: 1, names: ['element'], attributes: ['name'], children: true)
      ns = parser.node_set(ns[0].element_children, size: 2, index: 1, names: ['complexType'], children: true, xml: {0 => "<xs:annotation>\n\t\t\t<xs:documentation>ROOT element #{abbreviation}</xs:documentation>\n\t\t</xs:annotation>"})
      ns = parser.node_set(ns[1].element_children, size: 4, index: 0, names: ['sequence'], children: true, xml: {1..3 => %(<xs:attribute name="LG" type="t_ce_language_list" use="required"/><xs:attribute name="CATEGORY" type="original_translation" use="required"/><xs:attribute name="FORM" use="required" fixed="#{abbreviation}"/>)})
      ns = parser.node_set(ns[0].element_children, size: 4..8, names: %w(choice element), name_only: true)
      ns.to_enum.with_index(1) do |c, i|
        parser.elements(c, 0, index0: i)
      end

      parser.to_csv
    end
  end
end

task :label do
  forms('output', 'csv').each do |output|
    number = Integer(File.basename(output, '.csv').gsub(/\AF0?|_2014\z/, '')) - 1
    source = File.join('source', "XML Labels mapping R2.09_#{number}.csv")
    if File.exist?(source)
      labels = CSV.read(source, headers: true)

      form = CSV.read(output, headers: true)

      labels_map = {}
      labels.each do |row|
        name = row['XML element name']
        if name
          other = labels_map[name]
          if other
            difference = HashDiff.diff(row.to_h.except('Field ID'), other.to_h.except('Field ID'))
            if difference.any?
              puts "#{name}: #{difference}"
            end
          else
            labels_map[name] = row
          end
        end
      end

      # CONTINUE HERE

      # form_map = {}
      # form.each do |row|
      #   form_map[row['name']] = row
      #   form_map[row['ref']] = row
      # end
      # labels.each do |row|
      #   row['XML element name']
      #   form.
      # do naive matching of 'XML element name' to name in form or common

      # see how many don't match from XLSX

      # see how many are unmatched from XML/CSV
    end
  end
end

task review: :common do
  directories.each do |directory|
    text = File.read(File.join('output', 'common_2014.csv'))

    parser = XmlParser.new(File.join(directory, 'common_2014.xsd'))

    counts = Hash.new(0)
    %w(base ref type).each do |name|
      parser.schema.xpath(".//@#{name}").each do |attribute|
        counts[attribute.value] += 1
      end
    end

    $stderr.puts "\nFrequently occurring references:"
    counts.map{ |k, v|
      [text.scan(/,#{Regexp.escape(k)}\b/).count - v, k]
    }.sort.select{ |v, k| v > 1 }.each{ |v, k|
      $stderr.puts "#{v}: #{k}"
    }

    counts = Hash.new(0)
    text.scan(/\+,([^,\n]+)/).each do |s|
      counts[s[0]] += 1
    end

    $stderr.puts "\nFrequently occurring attributes:"
    counts.sort_by(&:last).each do |k, v|
      $stderr.puts "#{v}: #{k}"
    end
  end
end
