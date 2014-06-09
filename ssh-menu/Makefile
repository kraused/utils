
CC       = gcc
CPPFLAGS = 
CFLAGS   = 
LDFLAGS  = 
LIBS     = -lncurses

all: ssh-menu

ssh-menu: ssh-menu.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LIBS)

clean:
	-rm -f ssh-menu

