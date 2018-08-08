class TableBuilder
  def self.labels
    @labels ||= begin
      labels = {}

      # Ignore extra rows and columns.
      CSV.read(File.join('source', 'Forms labels R2.09.csv'), headers: true).each do |row|
        if row.fields.any?
          labels[row.delete('Label')[1]] = row.delete_if{ |_, v| v.nil? }.to_h
        end
      end

      labels
    end
  end

  def initialize(language)
    @language = language
    @targets = {}
    @output = ''
  end

  def add(text)
    @output << text
  end

  def to_s
    @output
  end

  def t(key)
    self.class.labels.fetch(key).fetch(@language)
  end

  # Helpers

  def heading(number, label)
    h2 "F#{number}: #{t(label)}"
  end

  def table(label=nil)
    start_table
    if label
      caption(t(label))
    end
    colgroup
    thead
    start_tbody
  end

  def row(label, help_labels: [], index: nil, xpath: false, value: false, guidance: false, reference: false)
    start_row
'See above'
    cell(index)

    if reference == false && guidance == false
      start_cell(colspan: 2)
      paragraph(t(label))
      end_cell
    else
      if xpath
        @targets[label] = xpath
      end

      content = t(label)
      help_labels.each do |help_label|
        content += " (#{t(help_label)})"
      end
      if xpath
        content += "<br> #{code(xpath)}"
      end
      if value
        content += "set to #{code(value)}"
      end

      if xpath
        start_cell(id: xpath)
      else
        start_cell
      end
      paragraph(content)
      end_cell
      if reference
        cell(link_to('See above', "##{@targets[label]}"))
      else
        cell(guidance) # TODO
      end
    end

    end_row
  end

  # HTML: Block

  def h2(text)
    add <<-END
<h2>#{text}</h2>

END
  end

  def start_table
    add <<-END
<div class="wy-table-responsive">
  <table class="docutils">
END
  end

  def end_table
    add <<-END
  </table>
</div>

END
  end

  def caption(text)
    add <<-END
    <caption>#{text}</caption>
END
  end

  def colgroup # TODO
    add <<-END
    <!--
    <colgroup>
      <col width="5%">
      <col width="45%">
      <col width="50%">
    </colgroup>
    -->
END
  end

  def thead
    add <<-END
    <thead>
      <tr>
        <th>Index</th>
        <th>Label and XPath</th>
        <th>OCDS guidance</th>
      </tr>
    </thead>
END
  end

  def start_tbody
    add <<-END
    <tbody>
END
  end

  def end_tbody
    add <<-END
    </tbody>
END
  end

  def start_row
    add <<-END
      <tr>
END
  end

  def end_row
    add <<-END
      </tr>
END
  end

  def start_cell(attributes = {})
    if attributes.any?
      add <<-END
        <td #{attributes.map{ |k, v| %(#{k}="#{v}") }.join(' ')}>
END
    else
      add <<-END
        <td>
END
    end
  end

  def end_cell
    add <<-END
        </td>
END
  end

  def cell(text)
    add <<-END
        <td>#{text}</td>
END
  end

  def paragraph(text)
    add <<-END
          <p>#{text}</p>
END
  end

  # HTML: Inline

  def link_to(text, target)
    %(<a href="#{target}">#{text}</a>)
  end

  def code(text)
    %(<code>#{text}</code>)
  end
end
