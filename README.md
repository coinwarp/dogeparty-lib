[![Build Status Travis](https://travis-ci.org/CounterpartyXCP/dogeparty-lib.svg?branch=develop)](https://travis-ci.org/CounterpartyXCP/dogeparty-lib)
[![Build Status Circle](https://circleci.com/gh/CounterpartyXCP/dogeparty-lib.svg?&style=shield)](https://circleci.com/gh/CounterpartyXCP/dogeparty-lib)
[![Coverage Status](https://coveralls.io/repos/CounterpartyXCP/dogeparty-lib/badge.png?branch=develop)](https://coveralls.io/r/CounterpartyXCP/dogeparty-lib?branch=develop)
[![Latest Version](https://pypip.in/version/dogeparty-lib/badge.svg)](https://pypi.python.org/pypi/dogeparty-lib/)
[![License](https://pypip.in/license/dogeparty-lib/badge.svg)](https://pypi.python.org/pypi/dogeparty-lib/)
[![Gitter chat](https://badges.gitter.im/gitterHQ/gitter.png)](https://gitter.im/CounterpartyXCP/General)


# Description
`dogeparty-lib` is the reference implementation of the [Counterparty Protocol](https://dogeparty.io).

**Note:** for the command-line interface that used to be called `dogepartyd`, see [`dogeparty-cli`](https://github.com/CounterpartyXCP/dogeparty-cli).


# Requirements
* Patched Dogecoin Core with the following options set:

	```
	rpcuser=dogecoinrpc
	rpcpassword=<password>
	server=1
	txindex=1
	addrindex=1
	rpcthreads=1000
	rpctimeout=300
	minrelaytxfee=0.00005
	limitfreerelay=0
	```


# Installation

```
$ git clone https://github.com/CounterpartyXCP/dogeparty-lib.git
$ cd dogeparty-lib
$ python3 setup.py install
```


# Usage

```
$ python3
>>> from dogepartylib import server
>>> db = server.initialise(<options>)
>>> server.start_all(db)
```


# Further Reading

* Official Project Documentation
