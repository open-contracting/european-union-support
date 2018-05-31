class TreeNode
  # @return [Hash] the node's attributes
  attr_accessor :attributes

  # Sets the node's known attributes and given attributes.
  #
  # @param [Nokogiri::XML::Node] node a node
  # @param [Hash] attrs attributes
  def initialize(node, attrs={})
    @node = node

    @attributes = {tag: node.name}
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
      raise "unexpected attributes #{difference} for #{@node.path}"
    end
  end

  # Merges other attributes into this object.
  #
  # @param [Nokogiri::XML::Node] node an other node
  # @param [Hash] attrs other attributes
  # @raise if the other attribute values conflict with this object's attribute values
  def merge(node, attrs, except: [])
    other = self.class.new(node, attrs)

    other.attributes = other.attributes.slice(*ASSIGNABLE - except)

    other.attributes.each do |k, v|
      value = attributes[k]
      if value && value != v
        raise "unexpected overwite of #{k} from #{value} to #{v}"
      end
    end

    update_attributes(other.attributes)
  end

  def to_s
    "#{super} #{attributes.inspect}"
  end
end
