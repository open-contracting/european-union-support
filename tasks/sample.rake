# Attempted to use existing software to generate XML from XSD:
#
# * Eclipse: Requires Java.
# * Visual Studio Community 2017 for Mac: Lacks XML Schema Explorer. Note: schemaLocation must be an absolute path to validate XSD.
# * OxygenXML: Can generate multiple samples, but no easy way to see choices, cardinality, restrictions, optional sequences, etc.

desc 'Create sample XML files from XSD files'
task :sample do
  FileUtils.mkdir_p('output/samples')

  case ENV['RELEASE']
  when 'R2.0.9', nil
    prefix = 'source/TED_publication_R2.0.9.S03.E01_007'
  when 'R2.0.8'
    prefix = 'source/TED_publication_R2.0.8.S04.E01_003'
  else
    raise "unexpected release: #{ENV['RELEASE']}"
  end

  files("#{prefix}/F{}*.xsd").each do |filename|
    builder = XMLBuilder.new(filename, release: ENV['RELEASE'])
    builder.build
    File.open("output/samples/#{builder.basename}.xml", 'w') do |f|
      f.write(builder.to_xml)
    end
  end
end
