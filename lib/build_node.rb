class BuildNode
  # @return [String] the node's tag name
  attr_reader :name
  # @return the arguments to build the node
  attr_reader :arguments
  # @return [Array<BuildNode>] the node's children
  attr_reader :children

  # @param [String] name the node's tag name
  # @param args the arguments to build the node
  def initialize(name, *args)
    @name = name
    @arguments = args
    @children = []

    if @arguments.empty?
      @arguments << {}
    end
  end
end
