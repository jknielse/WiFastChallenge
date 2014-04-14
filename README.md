WiFastChallenge
===============

Before you begin, make sure to install the following python libraries:

```bash
pip install requests
pip install unidecode
```

The specifics of the problem definition can be found in ProblemConfiguration.json, and can be re-defined if desired.

The general approach used to solve this problem was as follows:
- Determine which blocks might contain the transactions in question and download them
- Filter the transactions within the downloaded blocks to only ones that fit the filters in the config file (the filters in the config file were made by taking the highest and lowest value of bitcoins over the specified period to get an upper and lower bound on the transaction value)
- Make a list for each of the specified transactions, and append the addresses that were the sender(s) for any of the suspected transactions.
- Take the lists, and keep only those sending addresses that appear in all of the lists
- If there is still ambiguity, rank each address by "how well" the suspected transactions fit the filters. To do this, each suspected transaction is given a weight based on its distance from the mean of the filter (normalized by the bounds of the filter). 
- The sum of the weights of the best fitting transactions for each specified transaction are taken to be the weight of the suspect.
- The suspect with the lowest weight (implying closest to the filter means) is assumed to be the guilty party.