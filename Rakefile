require 'csv'
require 'delegate'
require 'securerandom'

require 'active_support/core_ext/hash/except'
require 'hashdiff'
require 'kramdown'
require 'nokogiri'
require 'regexp-examples'

require_relative 'lib/build_node'
require_relative 'lib/table_builder'
require_relative 'lib/xml_base'
require_relative 'lib/xml_builder'

ROMAN_NUMERALS = {
  '1' => 'I',
  '2' => 'II',
  '3' => 'III',
  '4' => 'IV',
  '5' => 'V',
  '6' => 'VI',
  '7' => 'VII',
}

# Modify RegexpExamples to exclude control characters.
# https://github.com/tom-lord/regexp-examples/blob/master/lib/regexp-examples/char_sets.rb
module RegexpExamples
  module CharSets
    def self.redefine(const, value)
      self.send(:remove_const, const)
      self.const_set(const, value)
    end

    redefine(:Any, Any - Control) # libxml2 errors on control characters
    redefine(:AnyNoNewLine, AnyNoNewLine - Control) # libxml2 errors on control characters
    redefine(:Whitespace, Whitespace - ["\f", "\v", "\r", "\n"]) # libxml2 errors on \f and \v, some types restrict \r and \n
    redefine(:BackslashCharMap, BackslashCharMap.merge('s' => Whitespace))
  end
end

def files(glob)
  if ENV['FILES']
    replacement = "{#{ENV['FILES']}}"
  else
    replacement = '*'
  end
  Dir[glob.sub('{}', replacement)].sort
end

def pdftotext(path)
  text_path = path.sub(/\.pdf/, '.txt')
  if File.exist?(text_path)
    lines = File.readlines(text_path, chomp: true)
  else
    lines = `pdftotext -layout #{path} -`.split("\n")
  end

  # Remove endnotes.
  lines = lines[0...lines.index{ |line| line['<<HD_reminder>>'] } || -1] + lines[lines.index{ |line| line[/<<annex_d\d>>/] } || -1...-1]
  # Remove footers.
  lines = lines.reject{ |line| line[/\A<<HD_ln>> <<standardform>> \d+ – <<\S+>> +\d+\z/] }

  lines.join("\n")
end

def label_keys(text)
  text.scan(/<<([^>]+)>>/).flatten
end

def indices(text)
  text.scan(/\bsection_(\d)\b/).flatten.map{ |number| ROMAN_NUMERALS.fetch(number) } + text.scan(/\b[IV]+(?:\.\d+)*/).flatten
end

def help_text?(key, number: nil)
  key[/\AHD?_/] ||
    %w(allocation_rest excl_vat icar_H_provide_numbers notice_design_cont request_qualification social_transfer_staff).include?(key) ||
    number == 'F08' && %w(directive_201424 directive_201425 directive_200981).include?(key)
end

# The same XSD is used for both T01 and T02, but each form uses different parts.
def select_move_rows(data, number)
  case number
  when 'T01'
    label_key = 'envisaged_start'
    pattern = 'AWARD_CONTRACT|LEFTI|OBJECT_CONTRACT/OBJECT_DESCR/ESSENTIAL_ASSETS'
  when 'T02'
    label_key = 'start_date_duration'
    pattern = 'PROCEDURE'
  else
    raise "unexpected form: #{number}"
  end
  data.find{ |row| row['xpath'] == '/OBJECT_CONTRACT/OBJECT_DESCR/DURATION' }['label-key'] = label_key
  data.reject{ |row| row['xpath'][%r{\A/(?:#{pattern})}] }
end

Dir['tasks/*.rake'].each { |r| import r }
Dir['legacy/*.rake'].each { |r| import r }
