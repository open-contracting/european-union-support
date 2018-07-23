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

def directories
  if ENV['DIRECTORY']
    directories = [ENV['DIRECTORY']]
  else
    directories = Dir[File.join('source', 'TED_*')].sort
  end
end

def files(directory, extension)
  suffix = "_2014.#{extension}"
  if ENV['FILES']
    ENV['FILES'].split(',').map{ |number| File.join(directory, "F#{number}#{suffix}") }
  else
    Dir[File.join(directory, "F*#{suffix}")].sort
  end
end

Dir['tasks/*.rake'].each { |r| import r }
Dir['legacy/*.rake'].each { |r| import r }
