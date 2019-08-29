desc 'Build a reference table of elements and labels'
task :reference do
  labels = TableBuilder.labels

  rows = Set.new
  files('output/mapping/{}*.csv').each do |filename|
    data = CSV.read(filename, headers: true)
    data.each do |row|
      rows << [row['xpath'], row['index'], row['label-key']]
    end
  end

  puts <<-END
# XPath reference

<div class="wy-table-responsive">
  <table class="docutils">
END

  rows.sort_by(&:first).each do |xpath, index, label_key|
    if label_key
      puts <<-END
    <tr>
      <td>#{index}</td>
      <td><code>#{xpath}</code></td>
    </tr>
    <tr>
      <td colspan="2">
        <dl class="docutils">
END

      labels.fetch(label_key).each do |code, label|
        puts <<-END
          <dt>#{code}</dt>
          <dd>#{label}</dd>
END
      end
    end

    puts <<-END
        <dl>
      </td>
    </tr>
END
  end

  puts <<-END
  </table>
</div>
END
end
