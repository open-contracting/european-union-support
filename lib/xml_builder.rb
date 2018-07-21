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
  def to_xml_recursive(nodes, xml)
    nodes.each do |node|
      if node.name == 'comment'
        xml.comment " #{node.content} "
      else
        attribute_nodes, element_nodes = node.children.partition do |child|
          child.attribute?
        end

        attributes, comments = {}, []
        attribute_nodes.each do |attribute_node|
          attributes[attribute_node.name] = attribute_node.content
          if attribute_node.comments.any?
            comments << attribute_node.comment
          end
        end

        if comments.any?
          xml.comment comments.join('|')
        end

        xml.send(node.name, attributes) do
          content = node.content
          if content
            xml.text content
          end
          if node.comments.any?
            xml.comment node.comment
          end
          to_xml_recursive(element_nodes, xml)
        end
      end
    end
  end

  # Returns a comment node.
  #
  # @return [BuildNode] the comment node
  def comment_node(comment)
    node = BuildNode.new('comment')
    node.contents << comment
    node
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
  # @param [Boolean] attribute whether the node is an attribute
  def add_node(n, pointer, attribute = false)
    node = BuildNode.new(n.attributes.fetch('name'), attribute)
    pointer.children.append(node)
    node
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
        namespace, reference = reference.split(':', 2)
      end

      node = lookup(reference, n.name)

      visit(node, pointer)

    elsif n.key?('type')
      reference = n['type']

      node = lookup(reference, 'complexType', 'simpleType')

      if node.name == 'complexType' && !ALWAYS_VISIT.include?(reference)
        if @types.key?(reference)
          pointer.children << comment_node("see #{@types[reference]}")
          return
        end
        @types[reference] = n.attributes.fetch('name')
      end
      visit(node, pointer)

    elsif n.key?('base')
      if n.name == 'extension'
        reference = n['base']

        node = lookup(reference, 'complexType', 'simpleType')

        visit(node, pointer)

      # Based on the analysis in `visit`, we can skip visiting `base` if within a `complexType`, but not if within a `simpleType`.
      elsif n.parent.name == 'simpleType'
        reference = n['base']
        if reference[':']
          namespace, reference = reference.split(':', 2)
        end

        if namespace != 'xs'
          node = lookup(reference, 'simpleType')

          visit(node, pointer)
        end
      end
    end

    n.element_children.each do |c|
      visit(c, pointer)
    end
  end

  # Visits a parsed node.
  #
  # @param [Nokogiri::XML::Node] n a node from the parser
  # @param [Nokogiri::XML::Node] pointer the current node in the tree
  def visit(n, pointer)
    # TODO if there's a comment (e.g. cardinality) on choice, sequence, group, need to show that it applies to the set, not the element
    case n.name
    when 'choice'
      # TODO add comment (or something) about choices
      comment(n, pointer)

    when 'sequence'
      # TODO nesting like procurement_address
      comment(n, pointer)

    when 'group'
      comment(n, pointer)

    when 'element'
      comment(n, pointer)
      if n.key?('name')
        pointer = add_node(n, pointer)
      end

    when 'attribute'
      pointer = add_node(n, pointer, true)

      # use is "required" on all xs:attribute except <xs:attribute name="PUBLICATION" type="publication"/>
      if n.key?('fixed')
        pointer.contents << n['fixed']
      else
        pointer.comments['use'] = n['use']
      end

    when 'enumeration'
      pointer.comments['enumeration'] ||= []
      pointer.comments['enumeration'] << n.attributes.fetch('value').value

    when 'maxLength'
      pointer.comments['maxLength'] = Integer(n.attributes.fetch('value').value)

    when 'maxInclusive'
      pointer.comments['maxInclusive'] = Integer(n.attributes.fetch('value').value)

    when 'minInclusive'
      pointer.comments['minInclusive'] = Integer(n.attributes.fetch('value').value)

    when 'minExclusive'
      pointer.comments['minExclusive'] = Integer(n.attributes.fetch('value').value)

    when 'pattern'
      pointer.comments['pattern'] = n.attributes.fetch('value').value

    when 'totalDigits'
      pointer.comments['totalDigits'] = Integer(n.attributes.fetch('value').value)

    when 'extension'
      # TODO logic

      # Every `complexType` node with a `complexContent` child with an `extension` child uses a base of:
      #
      # * contact_contractor        restricts contact
      # * agree_to_publication_man  defines attribute
      # * agree_to_publication_opt  defines attribute
      # * non_published             defines attribute
      # * lot_numbers               defines sequence
      # * text_ft_multi_lines       defines sequence
      # * val_range                 defines sequence
      #
      # See <xs:complexType( name="[^"]+")?>\s*<xs:complexContent>\s*<xs:extension base="(?!(agree_to_publication_man|agree_to_publication_opt|non_published|contact_contractor|lot_numbers|text_ft_multi_lines|val_range)")

      # Every `complexType` node with a `simpleContent` child with an `extension` child uses a base of:
      #
      # * val                       cost              attribute
      # * string_200                string_not_empty  maxLength
      # * duration_value_2d         _2car             minExclusive
      # * duration_value_3d         _3car             minExclusive
      # * duration_value_4d         _4car             minExclusive
      # * nb                        _3car             minExclusive
      # * date_full                 xs:date           pattern
      # * cost                      xs:decimal        minExclusive pattern
      # * customer_login            xs:string         pattern
      # * esender_login             xs:string         pattern
      # * no_doc_ext                xs:string         pattern
      # * string_not_empty          xs:string         pattern
      # * string_not_empty_nuts     xs:string         pattern
      #
      # See: <xs:complexType( name="[^"]+")?>\s*<xs:simpleContent>\s*<xs:extension base="(?!(cost|customer_login|date_full|duration_value_2d|duration_value_3d|duration_value_4d|esender_login|nb|no_doc_ext|string_200|string_not_empty|string_not_empty_nuts|val)")

    when 'restriction'
      # Every `complexType` node with a `restriction` grandchild uses a `base` of:
      #
      # * complement_info             defines sequence
      # * contact                     defines sequence
      # * contact_contracting_body    restricts contact
      # * lefti                       defines sequence
      # * lot_numbers                 defines sequence
      #
      # These bases have no attributes, therefore we don't need to visit them. https://www.w3.org/TR/xmlschema-0/#DerivByRestrict
      #
      # See: <xs:complexContent.+\s*<xs:restriction base="(?!(complement_info|contact|contact_contracting_body|lefti|lot_numbers)")

      # Every `simpleType` node with a `restriction` child uses a base of:
      #
      # * legal_basis                 lb:t_legal-basis_tedschema
      # * string_100                  string_not_empty            maxLength
      # * string_200                  string_not_empty            maxLength
      # * prct                        xs:integer                  maxInclusive, minExclusive
      # * _2car                       xs:nonNegativeInteger       totalDigits
      # * _3car                       xs:nonNegativeInteger       totalDigits
      # * _4car                       xs:nonNegativeInteger       totalDigits
      # * _5car                       xs:nonNegativeInteger       totalDigits
      # * cur:t_currency_tedschema    xs:string                   enumeration
      # * lb:t_legal-basis_tedschema  xs:string                   enumeration
      # * alphanum                    xs:string                   pattern
      # * string_not_empty            xs:string                   pattern
      # * string_with_letter          xs:string                   pattern
      # * xs:date
      # * xs:decimal
      # * xs:integer
      # * xs:nonNegativeInteger
      # * xs:string
      #
      # See: <xs:simpleType.+\s*(<xs:annotation>\s*<xs:documentation([^<]+|(\s*\S[^/x\n]+)+)\s*</xs:documentation>\s*</xs:annotation>\s*)?<xs:restriction base="
      # See: <xs:restriction base="(?!(_2car|_3car|_4car|_5car|alphanum|cur:t_currency_tedschema|lb:t_legal-basis_tedschema|legal_basis|prct|string_100|string_200|string_not_empty|string_with_letter|xs:decimal|xs:date|xs:integer|xs:nonNegativeInteger|xs:string|complement_info|contact|contact_contracting_body|lefti|lot_numbers)")

    when 'complexContent', 'simpleContent', 'complexType', 'simpleType'
      # Pass through.

    else
      raise "unexpected #{n.name}: #{n}"
    end

    follow(n, pointer)
  end
end
