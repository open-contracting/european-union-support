require 'csv'
require 'delegate'

# The script doesn't check whether all elements of the forms are visited during parsing, instead assuming the TED
# documentation is correct. See https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.2.Formstructure

require 'nokogiri'

# These known attributes will automatically be added to the built tree.
ATTRIBUTES = %i(name type minOccurs maxOccurs use fixed ref)
# These attributes are used internally to build a locator for a node in the tree.
LOCATORS   = %i(index0 index1 index2 index3 index4 index5)
# These are calculated or other non-XML attributes of the node.
OTHERS     = %i(path tag annotation base value)
# All known, locator and other attributes that can be assigned.
ASSIGNABLE = ATTRIBUTES + LOCATORS + OTHERS
# All known and other attributes, excluding internal locators.
PROPERTIES = ATTRIBUTES + OTHERS

# All `ASSIGNABLE`, but with `LOCATORS` replaced with `index`.
HEADERS = %i(index name type minOccurs maxOccurs use fixed ref path tag annotation base value)

class TreeNode
  # @return [Hash] the node's attributes
  attr_accessor :attributes

  # Sets the node's path, known attributes and given attributes.
  #
  # @param [Nokogiri::XML::Node] node a node
  # @param [Hash] attrs attributes
  def initialize(node, attrs={})
    self.attributes = {path: node.path}

    ATTRIBUTES.each do |k|
      if node.key?(k.to_s)
        attributes[k] = node[k]
      end
    end

    update_attributes(attrs)
  end

  # Sets the given attributes.
  #
  # @param [Hash] attrs attributes
  # @raise if an attribute name is unexpected
  def update_attributes(attrs)
    difference = attrs.keys - ASSIGNABLE
    if difference.empty?
      attributes.merge!(attrs)
    else
      raise "unexpected attributes #{difference} for #{path}"
    end
  end
end

class XmlParser
  # @return the built tree
  attr_reader :tree

  # @param [String] form the form's identifier
  # @param [Nokogiri::XML::NodeSet] the form's schema
  # @param [Nokogiri::XML::NodeSet] the TED common schema
  # @param [Nokogiri::XML::NodeSet] the TED countries schema
  def initialize(form, schema, common, countries)
    @form = form
    @schema = schema
    @common = common
    @countries = countries

    @tree = []
  end

  # Prints the built tree as a CSV to standard output.
  def to_csv
    CSV do |csv|
      csv << ['form'] + HEADERS
      tree.each do |node|
        if node.attributes.key?(:value)
          node.attributes[:value] = node.attributes[:value].join('|')
        end

        csv << [@form, node.attributes.values_at(*LOCATORS).compact.join('.')] + node.attributes.values_at(*PROPERTIES)
      end
    end
  end

  # @param condition
  # @param [String] message
  # @param [Nokogiri::XML::Node] node a node
  # @raise if the condition isn't met
  def assert(condition, message='', node=nil)
    unless condition
      message = "#{@form}: #{message}"
      if node
        message += " at #{node.path}: #{node}"
      end
      raise message
    end
  end

  # @raise if the actual value isn't the expected value
  def assert_equal(actual, expected, message='', node=nil)
    assert actual == expected, "expected #{expected}, got #{actual} #{message}"
  end

  # @raise if the first value is not included in the second value
  def assert_in(first, second, message='', node=nil)
    assert Array === second && second.include?(first), "expected #{second} to include '#{first}' #{message}"
  end

  # @param [Nokogiri::XML::Node] node a node
  # @raise if the node has children
  def assert_leaf(node)
    assert node.element_children.empty?, 'expected no children', node
  end

  # Checks whether a node set meets expectations.
  #
  # `:size`, `:allow_empty` and `:xml` are always tested. If `:name_only` is set, attributes and children are not tested.
  # If `:index` is set, only the node at that index is tested. Otherwise, all options and all nodes are tested.
  #
  # @param [Nokogiri::XML::NodeSet] ns a node set
  # @param [Hash] opts
  # @option opts [Integer] :size The expected number of nodes in the node set.
  # @option opts [Integer] :allow_empty The number of nodes in the node set can be zero.
  # @option opts [Hash] :xml A hash of array indices/slices to XML strings.
  # @option opts [Boolean] :name_only Only test `:size`, `:allow_empty`, `:xml` and `:names`.
  # @option opts [Integer] :index The index of the single node to test.
  # @option opts [String] :names The allowed tag names.
  # @option opts [Array<String>] :attributes The expected attribute names. `[]` by default.
  # @option opts [Array<String>] :required_attributes The names of required attributes if `:attributes` not used.
  # @option opts [Array<String>] :optional_attributes The names of optional attributes if `:attributes` not used.
  # @option opts [String, true] :children If omitted, the node(s) to test are expected to have no children. If `"text"`,
  #                                       they are expected to have no element children. If `true`, they are expected to
  #                                       have children. If `"any"`, there are no expectations.
  # @return the node set
  def node_set(ns, opts)
    # Check options.
    if opts.key?(:size) && opts.key?(:allow_empty)
      raise 'must not set both :size and :allow_empty'
    end
    if opts.key?(:attributes) && (opts.key?(:required_attributes) || opts.key?(:optional_attributes))
      raise 'must not set both :attributes and any of :required_attribute, :optional_attributes'
    end

    if opts.key?(:size)
      assert_equal ns.size, opts[:size], "elements: #{ns}"
    else
      assert opts[:allow_empty] || !ns.empty?, 'expected to be non-empty'
    end

    if opts[:xml]
      opts[:xml].each do |k, v|
        assert_equal ns[k].to_xml, v
      end
    end

    if opts.key?(:index)
      node(ns[opts[:index]], opts)
    else
      ns.each do |n|
        node(n, opts)
      end
    end

    ns
  end

  # Checks whether a node meets expectations.
  #
  # @param [Nokogiri::XML::Node] n
  # @param [Hash] opts
  # @see node_set
  def node(n, opts)
    assert_in n.name, opts.fetch(:names), 'tag name', n

    if !opts[:name_only]
      if opts.key?(:required_attributes) && opts.key?(:optional_attributes)
        opts[:required_attributes].each do |attribute|
          assert_in attribute, n.attributes.keys, 'attribute name', n
        end
        allowed_attributes(n, opts[:required_attributes] + opts[:optional_attributes])
      else
        assert_equal n.attributes.keys, opts.fetch(:attributes, []), 'attribute names', n
      end
    end

    if !opts[:name_only]
      assert !opts.key?(:children) && n.children.none? ||
        opts[:children] == 'text' && n.element_children.none? ||
        opts[:children] == true && n.children.any? ||
        opts[:children] == 'any', "expected #{opts[:children].inspect} children", n
    end
  end

  # Checks whether a node's attribute names are within an expected list.
  #
  # @param [Nokogiri::XML::Node] n
  # @param [Array] attributes
  def allowed_attributes(n, attributes=[])
    unexpected = n.attributes.keys - attributes
    assert unexpected.empty?, "unexpected attributes #{unexpected}", n
  end

  # Checks the form's schema and then the TED schemas for the given path.
  #
  # @param [String] path an XPath
  # @return [Nokogiri::XML::NodeSet] a nodeset
  def xpath(path)
    node_set = @schema.xpath(path)
    if node_set.empty?
      node_set = @common.xpath(path)
      if node_set.empty?
        node_set = @countries.xpath(path)
      end
    end
    node_set
  end

  # @return [Symbol] the symbol for the locator at this depth
  # @raise if the depth of the locator is unexpected
  def key_for_depth(depth)
    key = "index#{depth + 1}".to_sym
    if !LOCATORS.include?(key)
      raise "missing property #{key}"
    end
    key
  end

  # Builds the tree by traversing the XML from the given node.
  #
  # @param [Nokogiri::XML::Node] n a node
  # @param [Integer] depth the depth of the node
  # @param [Hash] opts
  # @option opts :index0
  # @option opts :index1
  # @option opts :index2
  # @option opts :index3
  # @option opts :index4
  # @option opts :index5
  # @option opts :tag
  def elements(n, depth, opts={})
    case n.name
    when 'sequence'
      allowed_attributes(n)
      ns = node_set(n.element_children, names: %w(element group sequence choice), name_only: true)
      ns.to_enum.with_index(1) do |n, i|
        elements(n, depth + 1, opts.merge(key_for_depth(depth) => i))
      end

    when 'choice'
      allowed_attributes(n)
      ns = node_set(n.element_children, names: %w(element group sequence), name_only: true)
      ns.to_enum.with_index(97) do |n, i|
        elements(n, depth + 1, opts.merge(key_for_depth(depth) => i.chr))
      end

    when 'element'
      tree << TreeNode.new(n, opts)

      allowed_attributes(n, %w(name type minOccurs maxOccurs ref))
      ns = node_set(n.element_children, allow_empty: true, names: %w(annotation complexType), name_only: true)
      ns.each do |n|
        elements(n, depth, opts)
      end

      # Check assumptions.
      annotation_only = n.element_children.all?{ |n| n.name == 'annotation' }

      assert [
        n.key?('type'),
        annotation_only && n.key?('ref'),
        !annotation_only && n.element_children.any?,
      ].one?, 'expected one of "type", "ref" or children', n

      # Follow references.
      if n.key?('type')
        type = xpath(%w(complex simple).map{ |prefix| "./xs:#{prefix}Type[@name='#{n['type']}']" }.join('|'))
        ns = node_set(type, size: 1, names: %w(complexType simpleType), attributes: ['name'], children: true)
        # TODO
      elsif n.key?('ref')
        if n['ref'] == 'n2016:NUTS'
          # TODO
        else
          ref = xpath("./xs:#{n.name}[@name='#{n['ref']}']")
          ns = node_set(ref, size: 1, names: [n.name], required_attributes: ['name'], optional_attributes: ['type'], children: 'any')
          # TODO
        end
      end

    when 'group'
      tree << TreeNode.new(n, opts)

      allowed_attributes(n, %w(minOccurs maxOccurs ref))
      ns = node_set(n.element_children, allow_empty: true, names: ['annotation'], name_only: true)
      ns.each do |n|
        elements(n, depth, opts.merge(tag: 'group'))
      end

      # TODO follow `ref` reference

    when 'annotation'
      allowed_attributes(n)
      ns = node_set(n.element_children, size: 1, names: ['documentation'], children: 'text')

      assert !tree.last.attributes.key?(:annotation), 'unexpected annotation', n
      tree.last.attributes[:annotation] = ns[0].text

    when 'complexType'
      allowed_attributes(n)
      ns = node_set(n.element_children, names: %w(attribute choice group sequence complexContent simpleContent), name_only: true) # TODO add annotation
      ns.each do |n|
        elements(n, depth, opts)
      end

    when 'attribute'
      tree << TreeNode.new(n, opts.merge(key_for_depth(depth) => '+'))

      allowed_attributes(n, %w(name type use fixed))
      # TODO follow `type` reference

      if n.element_children.any?
        ns = node_set(n.element_children, size: 1, names: ['simpleType'], children: true)
        ns = node_set(ns[0].element_children, size: 1, names: ['restriction'], attributes: ['base'], children: 'any')

        base = ns[0]['base']
        # TODO follow `base` reference

        ns = node_set(ns[0].element_children, allow_empty: true, names: ['enumeration'], attributes: ['value'])

        tree.last.update_attributes({
          base: base,
          value: ns.map{ |n| n['value'] },
        })
      end

    when 'simpleContent'
      allowed_attributes(n)
      ns = node_set(n.element_children, size: 1, names: ['extension'], attributes: ['base'], children: true)

      base = ns[0]['base']
      # TODO follow `base` reference

      ns = node_set(ns[0].element_children, size: 1, names: ['attribute'], required_attributes: ['name'], optional_attributes: %w(type use fixed))
      elements(ns[0], depth, opts)
      # TODO follow `type` reference

    when 'complexContent'
      allowed_attributes(n)
      ns = node_set(n.element_children, size: 1, names: %w(extension restriction), name_only: true)

      base = ns[0]['base']
      # TODO follow `base` reference

      case ns[0].name
      when 'extension'
        names = %w(attribute choice group sequence)
      when 'restriction'
        names = %w(sequence)
      else
        assert false, "unexpected #{n.name}", n
      end

      allowed_attributes(ns[0], %w(base))
      ns = node_set(ns[0].element_children, allow_empty: true, names: names, name_only: true)
      ns.each do |n|
        elements(n, depth, opts)
      end

    else
      assert false, "unexpected #{n.name}", n
    end
  end
end

task :download do
  # TODO download the necessary files
end

task :process do
  # http://publications.europa.eu/mdr/eprocurement/ted/specific_versions_new.html#div2
  Dir['TED_*_R2'].sort.each do |directory|
    common = Nokogiri::XML(File.read(File.join(directory, 'common_2014.xsd'))).xpath('/xs:schema')
    countries = Nokogiri::XML(File.read(File.join(directory, 'countries.xsd'))).xpath('/xs:schema')

    # Other files described at https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.1.Overview
    Dir[File.join(directory, 'F*_2014.xsd')].sort.each do |filename|
      basename = File.basename(filename, '.xsd')
      form = basename.sub('_2014', '')

      # Assume XML declaration, xs:schema attributes, and comments are irrelevant.
      schema = Nokogiri::XML(File.read(filename)).xpath('/xs:schema')
      parser = XmlParser.new(form, schema, common, countries)

      ns = parser.node_set(schema.xpath("./xs:element[@name='#{basename}']"), size: 1, names: ['element'], attributes: ['name'], children: true)
      ns = parser.node_set(ns[0].element_children, size: 2, index: 1, names: ['complexType'], children: true, xml: {0 => "<xs:annotation>\n\t\t\t<xs:documentation>ROOT element #{form}</xs:documentation>\n\t\t</xs:annotation>"})
      ns = parser.node_set(ns[1].element_children, size: 4, index: 0, names: ['sequence'], children: true, xml: {1..3 => %(<xs:attribute name="LG" type="t_ce_language_list" use="required"/><xs:attribute name="CATEGORY" type="original_translation" use="required"/><xs:attribute name="FORM" use="required" fixed="#{form}"/>)})
      ns = parser.node_set(ns[0].element_children, names: %w(choice element), name_only: true)

      # For each element in the form's main `sequence`:
      ns.to_enum.with_index(1) do |n, i|
        opts = {index0: i} # element is in a sequence

        parser.tree << TreeNode.new(n, opts)

        case n.name
        when 'choice'
          parser.allowed_attributes(n)
          ns = parser.node_set(ns[0].element_children, names: %w(element sequence), name_only: true)
          # TODO children

        when 'element' # TODO deduplicate with `elements` ?
          parser.allowed_attributes(n, %w(name type minOccurs maxOccurs))

          ns = parser.node_set(schema.xpath("./xs:complexType[@name='#{n['type']}']"), size: 1, names: ['complexType'], attributes: ['name'], children: true)

          ns = parser.node_set(ns[0].element_children, names: %w(annotation attribute complexContent choice sequence), name_only: true)
          ns.each do |ctn|
            parser.elements(ctn, 0, opts)
          end
        else
          parser.assert false, "unexpected #{n.name}", n
        end
      end

      parser.to_csv
    end
  end
end
