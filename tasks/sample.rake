task :sample do
  FileUtils.mkdir_p('samples')

  directories.each do |directory|
    forms(directory, 'xsd').each do |filename|
      builder = XMLBuilder.new(filename)
      builder.build
      File.open(File.join('samples', "#{builder.basename}.xml"), 'w') do |f|
        f.write(builder.to_xml)
      end
    end
  end
end
