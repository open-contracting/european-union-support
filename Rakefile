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
      csv << %w(form) + HEADERS
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
  # `:size` and `:allow_empty` are always tested, and one of the following:
  #
  # * If `:names` is set, nodes will be tested with `:names` only.
  # * If `:size` is set, the indexed node will be tested with remaining options.
  # * If `:names` and `:size` aren't set, all the nodes will be tested with remaining options.
  #
  # @param [Nokogiri::XML::NodeSet] ns a node set
  # @param [Hash] opts
  # @option opts [Integer] :size The expected number of nodes in the node set.
  # @option opts [Integer] :allow_empty The number of nodes in the node set can be zero.
  # @option opts [Integer] :index The index of the node to test. `0` by default.
  # @option opts [String] :names The allowed tag names.
  # @option opts [String] :name The tag name of the node(s) to test.
  # @option opts [Array<String>] :attributes The attribute names of the node(s) to test. `[]` by default.
  # @option opts [Array<String>] :required_attributes The names of required attributes if `:attributes` not used.
  # @option opts [Array<String>] :optional_attributes The names of optional attributes if `:attributes` not used.
  # @option opts [String, true] :children If omitted, the node(s) to test are expected to have no children. If `"text"`,
  #                                       they are expected to have no element children. If `true`, they are expected to
  #                                       have children. If `"any"`, there are no expectations.
  # @option opts :xml A hash of array indices/slices to XML strings.
  # @return the node set
  def node_set(ns, opts)
    # Check options.
    if opts.key?(:size) && opts.key?(:allow_empty)
      raise 'must not set both :size and :allow_empty'
    end
    if opts.key?(:index) && (opts.key?(:names) || !opts.key?(:size))
      raise 'must not set :index and :names, or :index without :size'
    end
    if opts.key?(:names) && (opts.key?(:name) || opts.key?(:attributes) || opts.key?(:required_attributes) || opts.key?(:optional_attributes) || opts.key?(:children) || opts.key?(:xml))
      raise 'must not set both :names and any of :name, :attributes, :required_attributes, :optional_attributes, :children, :xml'
    end

    # Common checks.
    if opts.key?(:size)
      assert_equal ns.size, opts[:size], "elements: #{ns}"
    else
      assert opts[:allow_empty] || !ns.empty?, 'expected to be non-empty'
    end

    # Specific checks.
    if !opts.key?(:size) && !opts.key?(:names)
      ns.each do |n|
        node(n, opts)
      end
    elsif opts.key?(:names) # need to check attributes and children separately
      ns.each do |n|
        assert_in n.name, opts[:names], 'tag name', n
      end
    elsif opts.key?(:size)
      i = opts[:index] || 0
      if opts[:xml]
        opts[:xml].each do |k, v|
          assert_equal ns[k].to_xml, v
        end
      end
      node(ns[i], opts)
    end

    ns
  end

  # Checks whether a node meets expectations.
  #
  # @param [Nokogiri::XML::Node] n
  # @param [Hash] opts
  # @see node_set
  def node(n, opts)
    if opts.key?(:names)
      assert_in n.name, opts[:names], 'tag name', n
    else
      assert_equal n.name, opts.fetch(:name), 'tag name', n
    end

    if !opts.key?(:names)
      if opts.key?(:required_attributes) && opts.key?(:optional_attributes)
        opts[:required_attributes].each do |attribute|
          assert_in attribute, n.attributes.keys, 'attribute name', n
        end
        allowed_attributes(n, opts[:required_attributes] + opts[:optional_attributes])
      else
        assert_equal n.attributes.keys, opts.fetch(:attributes, []), 'attribute names', n
      end
    end

    if !opts.key?(:names)
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
      ns = node_set(n.element_children, names: %w(element group sequence choice))
      ns.to_enum.with_index(1) do |n, i|
        elements(n, depth + 1, opts.merge(key_for_depth(depth) => i))
      end

    when 'choice'
      allowed_attributes(n)
      ns = node_set(n.element_children, names: %w(element group sequence))
      ns.to_enum.with_index(97) do |n, i|
        elements(n, depth + 1, opts.merge(key_for_depth(depth) => i.chr))
      end

    when 'element'
      tree << TreeNode.new(n, opts)

      allowed_attributes(n, %w(name type minOccurs maxOccurs ref))
      ns = node_set(n.element_children, names: %w(annotation complexType), allow_empty: true)
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
        $stderr.puts %w(complex simple).map{ |prefix| "./xs:#{prefix}Type[@name='#{n['type']}']" }.join('|')
        type = xpath(%w(complex simple).map{ |prefix| "./xs:#{prefix}Type[@name='#{n['type']}']" }.join('|'))
        ns = node_set(type, size: 1, names: %w(complexType simpleType), attributes: ['name'], children: true)
        # TODO
      elsif n.key?('ref')
        if n['ref'] == 'n2016:NUTS'
          # TODO
        else
          ref = xpath("./xs:#{n.name}[@name='#{n['ref']}']")
          ns = node_set(ref, size: 1, name: n.name, required_attributes: ['name'], optional_attributes: %w(type), children: 'any')
          # TODO
        end
      end

    when 'group'
      tree << TreeNode.new(n, opts)

      allowed_attributes(n, %w(minOccurs maxOccurs ref))
      ns = node_set(n.element_children, names: %w(annotation), allow_empty: true)
      ns.each do |n|
        elements(n, depth, opts.merge(tag: 'group'))
      end

      # TODO follow `ref` reference

    when 'annotation'
      allowed_attributes(n)
      ns = node_set(n.element_children, size: 1, name: 'documentation', children: 'text')

      assert !tree.last.attributes.key?(:annotation), 'unexpected annotation', n
      tree.last.attributes[:annotation] = ns[0].text

    when 'complexType'
      allowed_attributes(n)
      ns = node_set(n.element_children, names: %w(attribute choice group sequence complexContent simpleContent)) # TODO add annotation
      ns.each do |n|
        elements(n, depth, opts)
      end

    when 'attribute'
      tree << TreeNode.new(n, opts.merge(key_for_depth(depth) => '+'))

      allowed_attributes(n, %w(name type use fixed))
      # TODO follow `type` reference

      if n.element_children.any?
        ns = node_set(n.element_children, size: 1, name: 'simpleType', children: true)
        ns = node_set(ns[0].element_children, size: 1, name: 'restriction', attributes: ['base'], children: 'any')

        base = ns[0]['base']
        # TODO follow `base` reference

        ns = node_set(ns[0].element_children, name: 'enumeration', attributes: ['value'], allow_empty: true)

        tree.last.update_attributes({
          base: base,
          value: ns.map{ |n| n['value'] },
        })
      end

    when 'simpleContent'
      allowed_attributes(n)
      ns = node_set(n.element_children, size: 1, name: 'extension', attributes: ['base'], children: true)

      base = ns[0]['base']
      # TODO follow `base` reference

      ns = node_set(ns[0].element_children, size: 1, name: 'attribute', required_attributes: ['name'], optional_attributes: %w(type use fixed))
      elements(ns[0], depth, opts)
      # TODO follow `type` reference

    when 'complexContent'
      allowed_attributes(n)
      ns = node_set(n.element_children, size: 1, names: %w(extension restriction))

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
      ns = node_set(ns[0].element_children, names: names, allow_empty: true)
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

      ns = parser.node_set(schema.xpath("./xs:element[@name='#{basename}']"), size: 1, name: 'element', attributes: ['name'], children: true)
      ns = parser.node_set(ns[0].element_children, size: 2, index: 1, name: 'complexType', children: true, xml: {0 => "<xs:annotation>\n\t\t\t<xs:documentation>ROOT element #{form}</xs:documentation>\n\t\t</xs:annotation>"})
      ns = parser.node_set(ns[1].element_children, size: 4, name: 'sequence', children: true, xml: {1..3 => %(<xs:attribute name="LG" type="t_ce_language_list" use="required"/><xs:attribute name="CATEGORY" type="original_translation" use="required"/><xs:attribute name="FORM" use="required" fixed="#{form}"/>)})
      ns = parser.node_set(ns[0].element_children, names: %w(choice element))

      # For each element in the form's main `sequence`:
      ns.to_enum.with_index(1) do |n, i|
        opts = {index0: i} # element is in a sequence

        parser.tree << TreeNode.new(n, opts)

        case n.name
        when 'choice'
          parser.allowed_attributes(n)
          ns = parser.node_set(ns[0].element_children, names: %w(element sequence))
          # TODO children

        when 'element' # TODO deduplicate with `elements` ?
          parser.allowed_attributes(n, %w(name type minOccurs maxOccurs))

          ns = parser.node_set(schema.xpath("./xs:complexType[@name='#{n['type']}']"), size: 1, name: 'complexType', attributes: ['name'], children: true)

          ns = parser.node_set(ns[0].element_children, names: %w(annotation attribute complexContent choice sequence))
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
