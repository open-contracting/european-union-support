# Attempted to use existing software to generate XML from XSD:
#
# * Eclipse: Requires Java.
# * Visual Studio Community 2017 for Mac: Lacks XML Schema Explorer. Note: schemaLocation must be an absolute path to validate XSD.
# * OxygenXML: Can generate multiple samples, but no easy way to see choices, cardinality, restrictions, optional sequences, etc.

task :sample do
  FileUtils.mkdir_p('samples')

  files('source', 'TED_*', 'xsd').each do |filename|
    builder = XMLBuilder.new(filename)
    builder.build
    File.open(File.join('samples', "#{builder.basename}.xml"), 'w') do |f|
      f.write(builder.to_xml)
    end
  end
end
