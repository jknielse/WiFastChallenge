import requests
import json
from datetime import datetime, timedelta
from unidecode import unidecode
import calendar
import os.path, time
import sys
from pprint import pprint
import os


configFileName = "ProblemConfiguration.json"
blockDataFileName = "BlockData.json"
filteredTransactionsFileName = "FilteredTransactions.json"




#Load the problem configuration from the json file:
configData = open(configFileName)
config = json.load(configData)

importantAddresses = []
for info in config["filterInformation"]:
	importantAddresses.append(info["addr"])


def RetrieveData():
	#The first thing we'd like to do is retrieve all of the blacks relevent to the date range

	startDay = datetime(config["dateRange"]["start"]["year"],config["dateRange"]["start"]["month"],config["dateRange"]["start"]["day"])
	endDay = datetime(config["dateRange"]["end"]["year"],config["dateRange"]["end"]["month"],config["dateRange"]["end"]["day"])

	currentDay = startDay

	blockList = []

	while (currentDay <= endDay):
		#Get the time associated with the current day:
		daytime = calendar.timegm(startDay.utctimetuple()) * 1000
		#Create a request to retrieve all of the blocks for that day
		r = requests.get('http://blockchain.info/blocks/' + str(daytime) + '?format=json')
		blockList.extend(r.json()['blocks'])
		currentDay = currentDay + timedelta(1)

	#Now that we have all of the blocks that may have contained the transactions we're looking for, we need to retrieve all
	#of that actualy block information.

	with open(blockDataFileName, "w+") as myfile:
	    myfile.write("[")

	counter = 0
	maxCounter = len(blockList)
	for blockInfo in blockList:
		r = requests.get('http://blockchain.info/block-index/' + str(blockInfo['hash']) + '?format=json')

		with open(blockDataFileName, "a") as myfile:
			myfile.write(unidecode(r.text))
			if (counter != maxCounter - 1):
				myfile.write(",")
			else:
				myfile.write("]")

		
		counter = counter + 1
		sys.stdout.write("\rRetrieving Block Information... " + str((float(counter)/float(maxCounter)) * 100.0) + '%                                                  ')
		sys.stdout.flush()

	print "\nComplete"


def IsImportantOutboundPiece(outboundPiece):
	for condition in config["filterInformation"]:
		if(outboundPiece["addr"] == condition["addr"] and 
			outboundPiece["value"] >= condition["min"] * 100000000 and 
			outboundPiece["value"] <= condition["max"] * 100000000):
			return True


def FilterBlockData():
	#we need to take all of the transactions and filter them down into a list of transactions that we might
	#care about. This will make it easier to iterate on a solution.

	json_data=open(blockDataFileName)

	data = json.load(json_data)


	with open(filteredTransactionsFileName, "w+") as myfile:
	    myfile.write("[")

	counter = 0
	blockCounter = 0
	maxBlockCounter = len(data)


	for block in data:
		for transaction in block["tx"]:
			for outboundPieces in transaction["out"]:
				if (IsImportantOutboundPiece(outboundPieces)):
					with open(filteredTransactionsFileName, "a") as myfile:
						counter = counter + 1
						if (counter > 1):
							myfile.write(",")
						myfile.write(json.dumps(transaction))
						break


		blockCounter = blockCounter + 1

		sys.stdout.write("\rFiltering Transactions... " + str((float(blockCounter)/float(maxBlockCounter)) * 100.0) + '%                                                  ')
		sys.stdout.flush()

	print ""

	with open(filteredTransactionsFileName, "a") as myfile:
	    myfile.write("]")	


	json_data.close()


def CalculateWeight(transaction, outboundPiece):
	#First, find the filter that applies to the outbound address
	for eachFilter in config["filterInformation"]:
		if eachFilter["addr"] == outboundPiece["addr"] :
			#Now we need to determine how close this transaction value was to the filter mean:
			filterMean = 100000000 * (eachFilter["min"] + eachFilter["max"])/2
			filterRange = 100000000 * (eachFilter["max"] - eachFilter["min"])
			distanceFromMean = abs(filterMean - outboundPiece["value"])

			#What we return is the distance from the filter mean, normalized by the filter range.
			return(distanceFromMean/filterRange)

	return 0


def PerformAnalysis():
	#This dictionary is going to contain a list of addresses that made transactions with the important addresses.
	#The dictionsary needs to be initialized with the empty list for each entry:
	outAddressLists = {}

	#This dictionary is going to contain a similar list, but it's also going to contain a weighting factor based on
	#how well the particular transaction matches our filter estimate
	weightedOutAddressLists = {}
	for address in importantAddresses:
		outAddressLists[address] = []
		weightedOutAddressLists[address] = []

	json_data=open(filteredTransactionsFileName)

	transactions = json.load(json_data)

	for transaction in transactions:
		for outboundPiece in transaction["out"]:
			if(outboundPiece["addr"] in importantAddresses):
				for inboundPiece in transaction["inputs"]:
					outAddressLists[outboundPiece["addr"]].append(inboundPiece["prev_out"]["addr"])
					weightingFactor = CalculateWeight(transaction, outboundPiece)
					weightedOutAddressLists[outboundPiece["addr"]].append({"addr" : inboundPiece["prev_out"]["addr"], "weight" : weightingFactor})
				break

	#There may be duplicate entries in these lists, so we're going to remove duplicates from the lists:
	for address in importantAddresses:
		outAddressLists[address] = list(set(outAddressLists[address]))

	#now, we'll go through each member of the first out address list, and if that member appears in
	#all of the other lists as well, then we'll add it to a topSuspect list:

	topSuspects = []

	for address in outAddressLists[importantAddresses[0]]:
		shouldAppend = True
		for importantAddress in importantAddresses:
			if(not (address in outAddressLists[importantAddress])):
				shouldAppend = False
				break

		if (shouldAppend):
			topSuspects.append(address)


	if (len(topSuspects) == 0):
		print "There were no addresses found within the specified time period that match all of the transactions in the filter."
	elif (len(topSuspects) == 1):
		print "The prime suspect is " + topSuspects[0]
	else:
		print "The following suspect addresses have all made transactions consistent with every transaction in the filter:"
		pprint(topSuspects)

		#In order to narrow down the suspects, we're going to have a look at their *best* fitting transaction from the
		#weighted address lists:

		bestSuspect = topSuspects[0]
		bestSuspectWeight = -1
		for suspect in topSuspects:

			suspectWeight = 0
			for address in importantAddresses:
				weightedAddressList = weightedOutAddressLists[address]

				bestWeight = 1
				for weightInfo in weightedAddressList:
					if(weightInfo["addr"] == suspect and 
						bestWeight > weightInfo["weight"]):
						bestWeight = weightInfo["weight"]
				suspectWeight = suspectWeight + bestWeight

			print "Suspect: " + suspect + " Weight: " + str(suspectWeight)

			if(bestSuspectWeight == -1):
				bestSuspectWeight = suspectWeight
				bestSuspect = suspect
			elif(bestSuspectWeight > suspectWeight):
				bestSuspectWeight = suspectWeight
				bestSuspect = suspect


		print "The suspect who's transactions most closely match the means of the filters is:"
		print bestSuspect

	json_data.close()



#firstly, check whether we need to download any block data:
if (not os.path.isfile(blockDataFileName)) or (time.ctime(os.path.getmtime(blockDataFileName)) < time.ctime(os.path.getmtime(configFileName))):
	print "Block data non-existant or out-of-date. Downloading..."
	RetrieveData()
else:
	print "Block data already downloaded, proceeding to transaction filtering"

#Now check if we've already filtered that information or not
if (not os.path.isfile(filteredTransactionsFileName)) or (time.ctime(os.path.getmtime(filteredTransactionsFileName)) < time.ctime(os.path.getmtime(blockDataFileName))):
	print "Filtered transactions need recalculation..."
	FilterBlockData()
else:
	print "Filtered transactions already exist, proceeding with analysis"


PerformAnalysis()






