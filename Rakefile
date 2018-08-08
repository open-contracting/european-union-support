require 'csv'
require 'delegate'
require 'securerandom'

require 'active_support/core_ext/hash/except'
require 'hashdiff'
require 'nokogiri'
require 'regexp-examples'

require_relative 'lib/build_node'
require_relative 'lib/xml_base'
require_relative 'lib/xml_builder'

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
    glob = glob.sub('{}', "{#{ENV['FILES']}}")
  else
    glob = glob.sub('{}', '*')
  end
  Dir[glob].sort
end

def pdftotext(path)
  lines = `pdftotext -layout #{path} -`.split("\n")

  # Remove footers.
  lines.reject!{ |line| line[/\A<<HD_ln>> <<standardform>> \d+ – <<\S+>> +\d+\z/] }
  # Remove footnotes.
  lines.take_while{ |line| !line['<<HD_reminder>>'] }

  lines.join("\n")
end

def label_keys(text)
  text.scan(/<<([^>]+)>>/).flatten
end

def help_text?(key)
  key[/\AHD?_/]
end

Dir['tasks/*.rake'].each { |r| import r }
Dir['legacy/*.rake'].each { |r| import r }
