class XmlBase
  class << self
    attr_reader :xml
  end

  # Finds the `schema` tag of the XML document at the given path, and then recursively finds the `schema` tags of the
  # XML documents referenced by `include` or `import` tags.
  #
  # @return [Hash] the key is a file path and the value is the `schema` tag of an XML document
  def import(path)
    schemas = {}

    schemas[path] = parse(path)
    schemas[path].xpath('./xs:include|./xs:import').each do |n| # discard import's namespace
      schema_location = File.join(File.dirname(path), n['schemaLocation'])
      schemas.merge!(import(schema_location))
    end

    schemas
  end

  # @param [String] path a filename
  # @return [Nokogiri::XML::Node] the `schema` tag of the XML document at the given path
  def parse(path)
    # Assume the XML declaration, xs:schema attributes, and comments are irrelevant.
    self.class.xml[path] ||= Nokogiri::XML(File.read(path)).xpath('/xs:schema')[0]
  end

  # Checks the form's schema and then the TED schemas for the given path.
  #
  # @param [String] path an XPath
  # @return [Nokogiri::XML::NodeSet] a nodeset
  def xpath(path)
    @schemas.each do |s|
      nodes = s.xpath(path)
      if !nodes.empty?
        return nodes
      elsif !follow?
        return false
      end
    end
    []
  end

  # @return [Boolean] whether to lookup references in imports or includes
  def follow?
    true
  end
end
