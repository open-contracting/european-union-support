require 'csv'
require 'delegate'

require 'active_support/core_ext/hash/except'
require 'hashdiff'
require 'nokogiri'

require_relative 'lib/build_node'
require_relative 'lib/tree_node'
require_relative 'lib/xml_base'
require_relative 'lib/xml_builder'
require_relative 'lib/xml_parser'

def directories
  if ENV['DIRECTORY']
    directories = [ENV['DIRECTORY']]
  else
    directories = Dir[File.join('source', 'TED_*')].sort
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

Dir['tasks/*.rake'].each { |r| import r }
