task :sample do
  directories.each do |directory|
    forms(directory, 'xsd').each do |filename|
      builder = XMLBuilder.new(filename)
      builder.build
      puts builder.to_xml
    end
  end
end
