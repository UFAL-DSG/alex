#!/bin/bash

echo -n "This will delete all intermediate files from data/ lm/, hclg/, slu/. Are you sure you want to proceed (Y/N)? "
read -n 1 ANSWER
if echo "$ANSWER" | grep '^[yY]' ; then
    echo -e "\nOK."
else
    echo -e "\nInterrupting."
    exit 1
fi

echo "Saving last scores..."
cd slu/
./print_scores.sh >> ../scores-last.txt 2>&1
cd ..

echo "Deleting files..."
clear_dir(){

    cd $1
    TODEL=`cat .gitignore | sed 's/\n/ /g'`
    /bin/ls -d $TODEL 2> /dev/null | grep -vE '^(stops-add.txt|models|train.py|test.py)$' | xargs rm -r
    cd ..
}

clear_dir data
clear_dir lm
clear_dir hclg
clear_dir slu

echo "Moving logs..."
curdate=`date +%Y%d%m-%H%M%S`
for file in training-log* SLU-* Goog-* qsubmit.* scores-*; do
    if [ -e "$file" ]; then
        mv "$file" "old.$curdate.$file"
    fi
done
