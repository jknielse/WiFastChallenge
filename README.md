WiFastChallenge
===============

Before you begin, make sure to install the following python libraries:

```bash
pip install requests
pip install unidecode
```

The specifics of the problem definition can be found in ProblemConfiguration.json, and can be re-defined if desired.

To run the solution, simply run

```bash
python SnowmanAnalysis.py
```


The general approach used to solve this problem was as follows:
- Determine which blocks might contain the transactions in question and download them
- Filter the transactions within the downloaded blocks to only ones that fit the filters in the config file (the filters in the config file were made by taking the highest and lowest value of bitcoins over the specified period to get an upper and lower bound on the transaction value)
- Make a list for each of the specified transactions, and append the addresses that were the sender(s) for any of the suspected transactions.
- Take the lists, and keep only those sending addresses that appear in all of the lists
- If there is still ambiguity, rank each address by "how well" the suspected transactions fit the filters. To do this, each suspected transaction is given a weight based on its distance from the mean of the filter (normalized by the bounds of the filter). 
- The sum of the weights of the best fitting transactions for each specified transaction are taken to be the weight of the suspect.
- The suspect with the lowest weight (implying closest to the filter means) is assumed to be the guilty party.


## Notes

Since it takes a while to download all of the blocks in question, this solution makes sure not to re-download
everything every time you run it. The same goes for filtering. This was very helpful for debugging the analysis logic
because It allows you to run analysis in rapid succession without waiting a half hour and abusing the network connection.

If you alter the config file, the blocks will be re-downloaded. This was to make sure that if the date range changed, the appropriate
blocks would still be retrieved. It could have been made more efficiently (by checking the date range and only re-downloading when necessary),
or by requiring the entire block chain to be downloaded, but for the purpose of this excercise I felt that this solution was good enough.
