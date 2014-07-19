
.PHONY: install

install:
	install -m 500 mkpasswd 	$(HOME)/bin
	install -m 500 now      	$(HOME)/bin
	install -m 500 srm      	$(HOME)/bin
	install -m 500 archive-imap.py 	$(HOME)/bin/archive-imap

