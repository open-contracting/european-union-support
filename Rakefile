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

def release_pattern(extension, r209_prefix, r208_prefix=nil)
  case ENV['RELEASE']
  when 'R2.0.9', nil
    prefix = r209_prefix
  when 'R2.0.8'
    prefix = r208_prefix || r209_prefix
  else
    raise "unknown release '#{ENV['RELEASE']}'"
  end
  "#{prefix}/F{}*.#{extension}"
end

def files(glob)
  search = '{}'
  if ENV['FILES']
    if ENV['FILES'].split(',').map(&:to_i).all?(&:zero?)
      search = 'F{}'
    end
    replacement = "{#{ENV['FILES']}}"
  else
    replacement = '*'
  end
  Dir[glob.sub(search, replacement)].sort
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
  key[/\AHD?_/] || %w(excl_vat notice_design_cont request_qualification).include?(key) || number == '08' && %w(directive_201424 directive_201425 directive_200981).include?(key)
end

Dir['tasks/*.rake'].each { |r| import r }
Dir['legacy/*.rake'].each { |r| import r }
