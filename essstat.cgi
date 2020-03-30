#!/bin/sh
#
LOGGING_DIR="/var/log/essstat"

#
# Get the QUERY_STRING and arguments
#
OIFS="$IFS"	# Save the old internal field separator.
IFS="${IFS}&"	# Set the field separator to & and parse the QUERY_STRING at the ampersand.
set $QUERY_STRING
Args="$*"
IFS="$OIFS"


#
# Parse the individual "name=value" tokens from the CGI after we initialize local variables.
#
TPLhost=""
esFrom="`date +\%G`"	#default From date as January 1st of this year - only need specify the year
esTo="`date +\%G`z"	#default To date as now - only need specify the year and a letter s to make it 'big'
#
for i in $Args ;do
	# Set the field separator to =
	IFS="${OIFS}="
	set $i
	IFS="${OIFS}"

	case $1 in
		# Don't allow "/" changed to " ".
		esTPLhost)
			TPLhost="`echo $2 | sed 's|[\]||g' | sed 's|%20| |g'`"
			;;
		# Don't allow "/" changed to " ".
		esFrom)
			esFrom="`echo $2 | sed 's|[\]||g' | sed 's|%20| |g'`"
			;;
		esTo)
			esTo="`echo $2 | sed 's|[\]||g' | sed 's|%20| |g'`"
			;;
#		*)	echo "<hr>Warning:"\
#			     "<br>Unrecognized variable \'$1\' passed by FORM in QUERY_STRING.<hr>"
#			;;
	esac
done


#
# We'll support a span of the From and To dates across a maximum of two years.
#
esFromY="${esFrom:0:4}"
esToY="${esTo:0:4}"

FilesToProcess="$LOGGING_DIR/essstat-$TPLhost-$esToY.csv"
if [ "$esFromY" != "$esToY" ]
then
	f2="$LOGGING_DIR/essstat-$TPLhost-$esFromY.csv"
	if test -f "$f2"
	then
	   FilesToProcess="$f2 $FilesToProcess"
	fi
fi


#
# Basic parameter check - return 400 status if a problem, otherwise try to return data
#
#logger -i $FilesToProcess
#logger -i "esFrom=$esFrom"
#logger -i "esTo=$esTo"
#
if [ "$TPLhost" == "" ]
then
        echo "Status: 400 Bad Request"
	echo ""
        echo "Bad parameters"
	echo ""
else
	echo "Content-type: text/plain"
	echo ""
	awk -F "," -v esFrom="$esFrom" -v esTo="$esTo"-- "(\$1 >= esFrom) && (\$1 <= esTo) {print \$0}"  $FilesToProcess
fi
