# I don't know a way to match lines programmatically in Vim (Ex mode). So, I grep for line numbers and then use Vim
# commands. This means that I can't run multiple commands at once if they change the line order. To make things easier,
# move lines into position from top to bottom.

function m_line -a glob -a source -a destination
    echo -c (grep -n $source {$glob}*.csv | cut -d: -f1)m(grep -n $destination {$glob}*.csv | cut -d: -f1)
end

function m_range -a glob -a start -a stop -a destination
    echo -c (grep -n $start {$glob}*.csv | cut -d: -f1),(grep -n $stop {$glob}*.csv | cut -d: -f1)m(grep -n $destination {$glob}*.csv | cut -d: -f1)
end

# Move the line matching source after the line matching destination.
function move_line -a glob -a source -a destination
    ex --noplugin -s -V1 (m_line $glob $source $destination) -c wq {$glob}*.csv
end

function move_range -a glob -a start -a stop -a destination
    ex --noplugin -s -V1 (m_range $glob $start $stop $destination) -c wq {$glob}*.csv
end

function move_range_to_end -a glob -a start -a stop
    ex --noplugin -s -V1 -c (grep -n $start {$glob}*.csv | cut -d: -f1),(grep -n $stop {$glob}*.csv | cut -d: -f1)m\$ -c wq {$glob}*.csv
end

cd output/mapping

# F03, F06, F15 only: `LOT_DIVISION` after `SHORT_DESCR`
for i in F03 F06 F15
    move_line $i /LOT_DIVISION OBJECT_CONTRACT/SHORT_DESCR
end

# F25 only: `LOT_DIVISION` after `CALCULATION_METHOD`
for i in F25
    move_line $i /LOT_DIVISION CALCULATION_METHOD
end

# F21, F22, F23 only: `VAL_TOTAL`, `VAL_RANGE_TOTAL`, and children after `LOT_COMBINING_CONTRACT_RIGHT`
for i in F21 F22 F23
    set l (grep -n OBJECT_CONTRACT/VAL_TOTAL, {$i}*.csv | cut -d: -f1)
    ex --noplugin -s -V1 -c $l,$l+5m(grep -n LOT_COMBINING_CONTRACT_RIGHT {$i}*.csv | cut -d: -f1) -c wq {$i}*.csv
end

# F03, F06, F15, F25 only: `NO_AWARDED_TO_GROUP` after `AWARDED_TO_GROUP`
for i in F03 F06 F15 F25
    move_line $i /NO_AWARDED_TO_GROUP /AWARDED_TO_GROUP
end
for i in F20
    for x in AWARDED_CONTRACT DESCRIPTION_PROCUREMENT
        move_line $i $x/CONTRACTORS/NO_AWARDED_TO_GROUP $x/CONTRACTORS/AWARDED_TO_GROUP
    end
end

# F03, F06, F21, F22 only: `D_ACCORDANCE_ARTICLE` and children after all
for i in F03 F06 F21 F22 F23 F25
    move_range_to_end $i D_ACCORDANCE_ARTICLE, D_JUSTIFICATION
end

for i in F15
    move_range $i OBJECT_DESCR/DIRECTIVE_2014_23_EU, DIRECTIVE_2014_23_EU/AC/ DIRECTIVE_2014_25_EU/AC/AC_PRICE/
    move_range $i PROCEDURE/DIRECTIVE_2014_23_EU, DIRECTIVE_2014_23_EU/PT_AWARD_CONTRACT_WITHOUT_PUBLICATION, DIRECTIVE_2009_81_EC/PT_NEGOTIATED_WITHOUT_PUBLICATION,
    move_line $i DIRECTIVE_2014_23_EU/PT_AWARD_CONTRACT_WITHOUT_CALL, DIRECTIVE_2014_23_EU/PT_AWARD_CONTRACT_WITHOUT_PUBLICATION,
    move_line $i DIRECTIVE_2009_81_EC/PT_AWARD_CONTRACT_WITHOUT_CALL, DIRECTIVE_2014_23_EU/PT_AWARD_CONTRACT_WITHOUT_PUBLICATION,
    move_line $i DIRECTIVE_2014_25_EU/PT_AWARD_CONTRACT_WITHOUT_CALL, DIRECTIVE_2014_23_EU/PT_AWARD_CONTRACT_WITHOUT_PUBLICATION,
    move_line $i DIRECTIVE_2014_24_EU/PT_AWARD_CONTRACT_WITHOUT_CALL, DIRECTIVE_2014_23_EU/PT_AWARD_CONTRACT_WITHOUT_PUBLICATION,

    for x in DIRECTIVE_2014_24_EU DIRECTIVE_2014_25_EU DIRECTIVE_2009_81_EC
        move_range_to_end $i $x/PT_NEGOTIATED_WITHOUT_PUBLICATION/D_ACCORDANCE_ARTICLE, $x/PT_AWARD_CONTRACT_WITHOUT_CALL/D_JUSTIFICATION
    end
    for x in DIRECTIVE_2014_23_EU
        move_range_to_end $i $x/PT_AWARD_CONTRACT_WITHOUT_PUBLICATION/D_ACCORDANCE_ARTICLE, $x/PT_AWARD_CONTRACT_WITHOUT_CALL/D_JUSTIFICATION
    end
end

# `NUTS` after `TOWN`
for i in F01 F02 F03 F04 F05 F06 F07 F08 F12 F13 F14 F15 F20 F21 F22 F23 F24 F25 MOVE
    move_line $i ADDRESS_CONTRACTING_BODY/NUTS, ADDRESS_CONTRACTING_BODY/TOWN,
end
for i in F03 F06 F15 F22 F23
    move_line $i ADDRESS_CONTRACTOR/NUTS, ADDRESS_CONTRACTOR/TOWN,
end
for i in F13
    move_line $i ADDRESS_WINNER/NUTS, ADDRESS_WINNER/TOWN,
end

# `NO_LOT_DIVISION` after `LOT_DIVISION`
for i in F01 F02 F03 F04 F05 F06 F15 F21 F23 F24 F25
    move_line $i /NO_LOT_DIVISION, /LOT_DIVISION,
end
