
.PHONY: install

install:
	install -m 500 mkpasswd.py 	$(HOME)/bin/mkpasswd
	install -m 500 now      	$(HOME)/bin
	install -m 500 srm      	$(HOME)/bin
	install -m 500 archive-imap.py 	$(HOME)/bin/archive-imap
	install -m 500 sanitize.py 	$(HOME)/bin/sanitize

