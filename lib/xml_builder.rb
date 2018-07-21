class XMLBuilder < XmlBase
  @xml = {}

  ALWAYS_VISIT = %w(
    empty
    ft
    p
    text_ft_multi_lines
    text_ft_single_line
  )

  # @param [String] path the path to the XSD file
  def initialize(path)
    @basename = File.basename(path, '.xsd')
    @schemas = import(path).values
    @schema = @schemas[0]

    @schemas.each do |schema|
      schema.xpath('.//xs:annotation').remove
      schema.xpath('.//xs:unique').remove
    end

    reset
  end

  # Reset the builder.
  def reset
    @root = BuildNode.new(nil)
    @types = {}
  end

  # Builds the sample XML document for the schema.
  def build
    reset
    visit(root, @root)
  end

  # Returns the schema's root node.
  #
  # @return [Nokogiri::XML::Node] the schema's root node
  def root
    @schema.xpath("./xs:element[@name='#{@basename}']")[0]
  end

  # Builds the XML document.
  #
  # @return [String] the built XML
  def to_xml
    Nokogiri::XML::Builder.new do |xml|
      to_xml_recursive(@root.children, xml)
    end.to_xml
  end

  # Recursively adds nodes to the XML document.
  def to_xml_recursive(children, xml)
    children.each do |child|
      xml.send(child.name, *child.arguments) do
        to_xml_recursive(child.children, xml)
      end
    end
  end

  # Returns a comment node.
  #
  # @return [BuildNode] the comment node
  def comment_node(comment)
    BuildNode.new('comment', " #{comment} ")
  end


  # Adds a comment for the parsed node's attributes.
  #
  # Call `comment` before `add_node` to add the comment before its corresponding node.
  #
  # @param [Nokogiri::XML::Node] n a node from the parser
  # @param [Nokogiri::XML::Node] pointer the current node in the tree
  def comment(n, pointer)
    comments = []

    # mixed is "true" on p and text_ft_multi_lines_or_string only

    minOccurs = n['minOccurs'] || 1
    maxOccurs = n['maxOccurs'] || 1
    if minOccurs != 1 || maxOccurs != 1
      # XXX if 0-1, do something simpler to indicate "optional"
      comments << %(cardinality="[#{minOccurs}, #{maxOccurs}]")
    end

    if comments.any?
      pointer.children << comment_node(comments.join(' '))
    end
  end

  # Adds a parsed node to the tree.
  #
  # @param [Nokogiri::XML::Node] n a node from the parser
  # @param [Nokogiri::XML::Node] pointer the current node in the tree
  def add_node(n, pointer)
    node = BuildNode.new(n.attributes.fetch('name'))
    pointer.children.append(node)
    node
  end

  # Adds parsed attributes to the current node.
  #
  # Call `attribute` after `add_node` to add the attributes to the corresponding node.
  #
  # @param [Nokogiri::XML::Node] n a node from the parser
  # @param [Nokogiri::XML::Node] pointer the current node in the tree
  def attribute(n, pointer)
    attributes = {}
    nodes = n.xpath('./xs:attribute')

    nodes.each do |node|
      name = node.attributes.fetch('name')
      if node.key?('fixed')
        attributes[name] = node['fixed']
      else
        # XXX set value more intelligently
        # use is "required" on all xs:attribute except <xs:attribute name="PUBLICATION" type="publication"/>
        attributes[name] = n['use'] || 'foo'
      end
      follow(node, pointer)
    end

    nodes.remove
    pointer.arguments[0].merge!(attributes)
  end

  def lookup(name, *tags)
    xpath(tags.map{ |tag| "./xs:#{tag}[@name='#{name}']" }.join('|'))[0]
  end

  # Follows the references or visits the children of a parsed node.
  #
  # @param [Nokogiri::XML::Node] n a node from the parser
  # @param [Nokogiri::XML::Node] pointer the current node in the tree
  def follow(n, pointer)
    # We already checked that nodes have at most one of these in the XmlParser.
    if n.key?('ref')
      reference = n['ref']

      if reference[':']
        reference = reference.split(':', 2)[1]
      end

      node = lookup(reference, n.name)

      visit(node, pointer)

    elsif n.key?('type')
      reference = n['type']

      node = lookup(reference, 'complexType', 'simpleType')

      if node.name == 'complexType' && !ALWAYS_VISIT.include?(reference)
        if @types.key?(reference)
          pointer.children << comment_node("See #{@types[reference]}")
          return
        end
        @types[reference] = n.attributes.fetch('name')
      end
      visit(node, pointer)

    else
      # Based on the following analysis, we can visit a restricted node's children as if it were unrestricted.
      #
      # Every `complexType` node with a `restriction` grandchild uses a `base` of:
      #
      # * complement_info
      # * contact
      # * contact_contracting_body
      # * lefti
      # * lot_numbers
      #
      # See: <xs:complexContent.+\s*<xs:restriction base="(?!(complement_info|contact|contact_contracting_body|lefti|lot_numbers)")
      #
      # These bases have no attributes, therefore we don't need to visit them.
      #
      # See: https://www.w3.org/TR/xmlschema-0/#DerivByRestrict
      # See: https://stackoverflow.com/a/14801341/244258

      # Every `simpleType` node with a `restriction` child uses a base of:
      #
      # * _2car                       xs:nonNegativeInteger       totalDigits
      # * _3car                       xs:nonNegativeInteger       totalDigits
      # * _4car                       xs:nonNegativeInteger       totalDigits
      # * _5car                       xs:nonNegativeInteger       totalDigits
      # * alphanum                    xs:string                   pattern
      # * string_not_empty            xs:string                   pattern
      # * string_with_letter          xs:string                   pattern
      # * cur:t_currency_tedschema    xs:string                   enumeration
      # * lb:t_legal-basis_tedschema  xs:string                   enumeration
      # * string_100                  string_not_empty            maxLength
      # * string_200                  string_not_empty            maxLength
      # * prct                        xs:integer                  maxInclusive, minExclusive
      # * legal_basis                 lb:t_legal-basis_tedschema
      # * xs:date
      # * xs:decimal
      # * xs:integer
      # * xs:nonNegativeInteger
      # * xs:string
      #
      # See: <xs:simpleType.+\s*(<xs:annotation>\s*<xs:documentation([^<]+|(\s*\S[^/x\n]+)+)\s*</xs:documentation>\s*</xs:annotation>\s*)?<xs:restriction base="
      # See: <xs:restriction base="(?!(_2car|_3car|_4car|_5car|alphanum|cur:t_currency_tedschema|lb:t_legal-basis_tedschema|legal_basis|prct|string_100|string_200|string_not_empty|string_with_letter|xs:decimal|xs:date|xs:integer|xs:nonNegativeInteger|xs:string|complement_info|contact|contact_contracting_body|lefti|lot_numbers)")
      #
      # Note: The two enumerations have annotations with English labels in separate files.

      n.element_children.each do |c|
        visit(c, pointer)
      end
    end
  end

  # Visits a parsed node.
  #
  # @param [Nokogiri::XML::Node] n a node from the parser
  # @param [Nokogiri::XML::Node] pointer the current node in the tree
  def visit(n, pointer)
    case n.name
    when 'choice'
      # TODO add comment about choices
      # TODO if there's a comment on choice, sequence, group, need to show that it applies to the set, not the element
      comment(n, pointer)

    when 'sequence'
      # TODO nesting
      comment(n, pointer)

    when 'group'
      comment(n, pointer)

    when 'element'
      comment(n, pointer)
      if n.key?('name')
        pointer = add_node(n, pointer)
      end

    when 'complexType'
      attribute(n, pointer)

    when 'simpleContent'
      # TODO extension attribute()

    when 'extension'
      # TODO logic
      attribute(n, pointer)

    when 'complexContent'
      # TODO extension attribute()

    when 'enumeration', 'maxLength', 'maxInclusive', 'minInclusive', 'minExclusive', 'pattern'
      # XXX use to generate a value, see comment in `follow`

    # Visit the children.
    when 'restriction', 'simpleType'

    else
      raise "unexpected #{n.name}: #{n}"
    end
    follow(n, pointer)
  end
end
