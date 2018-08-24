class BuildNode
  # Low to high.
  ATTRIBUTE_PRIORITY = %w(
    use
    totalDigits
    minInclusive
    minExclusive
    maxExclusive
    maxInclusive
    maxLength
    pattern
    enumeration
  )

  # @return [String] the node's tag name
  attr_reader :name
  # @return [String] the node's parent
  attr_reader :parent
  # @return [Array<BuildNode>] the node's children
  attr_reader :children
  # @return [Array<BuildNode>] the node's contents
  attr_accessor :contents
  # @return [Array<BuildNode>] the node's comments
  attr_accessor :comments

  # @param [String] name the node's tag name
  # @param [BuildNode] parent the node's parent
  # @param [Boolean] attribute whether the node is an attribute
  def initialize(name, parent: nil, attribute: false)
    @name = name
    @parent = parent
    @attribute = attribute
    @children = []
    @contents = []
    @comments = {}
  end

  # @return [Boolean] whether the node is an attribute
  def attribute?
    @attribute
  end

  # @return [String] the node's content
  def content
    # This method has side-effects, so its return value must be cached.
    if @contents.any?
      @contents.join(', ')
    else
      default_content
    end
  end

  # @return [String] the node's default content
  def default_content
    # This method has side-effects, so its return value must be cached.
    attribute = ATTRIBUTE_PRIORITY.reverse.find{ |attribute| comments.key?(attribute) }

    if attribute
      value = comments[attribute]
      case attribute
      when 'enumeration'
        (value - ['NO']).sample # special case for `prune!`
      when 'maxLength'
        "maxLength #{comments.delete(attribute)}"
      when 'pattern'
        value = comments.delete(attribute)
        if value == '(19|20).{8}' # base="xs:date"
          value = /(19|20)\d\d-\d\d-\d\d/
        end
        Regexp.new(value).random_example # (max_repeater_variance: 10)
      when 'maxExclusive', 'maxInclusive', 'minExclusive', 'minInclusive', 'totalDigits'
        rand(minimum..maximum)
      else
        value
      end
    end
  end

  # @return [Integer] the node's maximum value
  def maximum
    if comments.key?('maxExclusive')
      comments['maxExclusive'] - 1
    elsif comments.key?('maxInclusive')
      comments['maxInclusive']
    # totalDigits is used on xs:nonNegativeInteger and xs:integer only, not on xs:decimal, etc.
    elsif comments.key?('totalDigits')
      Integer('9' * comments['totalDigits'])
    else
      0
    end
  end

  # @return [Integer] the node's minimum value
  def minimum
    if comments.key?('minExclusive')
      comments['minExclusive'] + 1
    elsif comments.key?('minInclusive')
      comments['minInclusive']
    else
      0
    end
  end

  # @return [String] the node's comment
  def comment
    parts = []
    if attribute?
      parts << name
    end
    parts << comments.sort_by{ |k, v| ATTRIBUTE_PRIORITY.index(k) || -1 }.map{ |k, v| %(#{k}="#{v}") }.join(' ')
    " #{parts.join(' ')} "
  end
end
