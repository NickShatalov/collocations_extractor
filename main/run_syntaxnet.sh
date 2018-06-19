if [ "$1" == "" ]; then
echo "Error: enter input filename"
exit 1
fi

if [ "$2" == "" ]; then
echo "Error: enter output filename"
exit 1
fi

cat $(pwd)/$1 | docker run --rm -i inemo/syntaxnet_eng > $(pwd)/$2

