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

ProcessFile2="$LOGGING_DIR/essstat-$TPLhost-$esToY.csv"
if [ "$esFromY" != "$esToY" ]
then
	ProcessFile1="$LOGGING_DIR/essstat-$TPLhost-$esFromY.csv"
	if [ ! -e "$ProcessFile1" ]
	then
	   ProcessFile1=""
	fi
fi


#
# Basic parameter check - return 400 status if a problem, otherwise try to return data
#
#logger -i "$ProcessFile1 $ProcessFile2"
#logger -i "esFrom=$esFrom"
#logger -i "esTo=$esTo"
#logger -i "QUERY_STRING=$QUERY_STRING"
#logger -i "HTTP_USER_AGENT=$HTTP_USER_AGENT"
#logger -i "REQUEST_METHOD=$REQUEST_METHOD"
#
if [ ! -e "$ProcessFile1" ] && [ ! -e "$ProcessFile2" ]
then
        #echo "Status: 404 Not Found"
	#echo ""
        #echo "No data for TPLhost over time range"
	#
	# Once we return an error status, Excel won't try any URL again until we close and re-open the workbook
	# To avoid this annoyance, just return normally with an empty payload
	echo "Content-type: text/plain"		
	echo ""
elif [ "$REQUEST_METHOD" == "HEAD" ]
then						#Supress extra calls by Excel
	echo "Content-type: text/plain"
	echo ""
else
	echo "Content-type: text/plain"
	echo ""
        echo "`cat ${ProcessFile1} ${ProcessFile2}`" | awk -F "," -v esFrom="$esFrom" -v esTo="$esTo" '
(NR == 1) {
	split($0, aLastRec, ",")
	t1 = $1
	gsub(/[-:]/, " ", t1)
	aLastRec[1] = strftime("%Y-%m-%d %H:%M:%S", mktime(t1)-1)
        split($0, aLast2Rec, ",")
	aLast2Rec[1] = strftime("%Y-%m-%d %H:%M:%S", mktime(t1)-2)
	delta2T = 1
}


($1 >= esFrom) && ($1 <= esTo) {
	PortCount = $2

	t1 = $1
	gsub(/[-:]/, " ", t1)
	t2 = aLastRec[1]
	gsub(/[-:]/, " ", t2)
	deltaT = mktime(t1) - mktime(t2)

	printf("%d,%s,%d", deltaT, $1, PortCount)

	for (i=0; i<PortCount; i++) {					#loop over the ports
	   #
	   # For each stat, calculate the PPS rate and check for negative. This
	   # can happen if the counter for the port wraps the maximum integer value,
	   # and automatically resets its value to zero. IN this case, the count from
	   # the current record will be less than the count from the previous record.
	   # If we encounter this, report back the PPS calculated for the previous record.
	   #
	   for (j=6; j<=9; j++) {
		if ( $((i*7)+j) < aLastRec[((i*7)+j)] )
		   aPPS[j] = (aLastRec[((i*7)+j)] - aLast2Rec[((i*7)+j)]) / delta2T
		else
		   aPPS[j] = ($((i*7)+j) - aLastRec[((i*7)+j)]) / deltaT
	   }
	   printf(",%d,%d,%d", $((i*7)+3), $((i*7)+4), $((i*7)+5))	#port number, state, link
	   printf(",%d,%d,%d,%d", aPPS[6], aPPS[7], aPPS[8], aPPS[9])
	}
	print ""
	delta2T = deltaT
}

 {
	for (i in aLastRec) aLast2Rec[i] = aLastRec[i]
	split($0, aLastRec, ",")
}
'


fi
