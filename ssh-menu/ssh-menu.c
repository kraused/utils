
#define _GNU_SOURCE

#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#include <curses.h>

#include <errno.h>
#include <unistd.h>


#define unlikely(x)	__builtin_expect(!!(x), 0)
#define   likely(x)	__builtin_expect(!!(x), 1)

#define STRLEN		128
#define MAX_ARGS	16

#define SSH		"/usr/bin/ssh"
#define RCFILE		".ssh/menu"

/*
 * Representation of (remote) host.
 */
struct entry {
	char	name[STRLEN];

	char	host[STRLEN];
	char	user[STRLEN];
	char	descr[STRLEN];

	/* There are three options. If both fqdn and ip are
	 * empty we assume that the host is specified in the
	 * ssh config file. Otherwise, either the fqdn or
	 * the ip are used. We prefer to use the fqdn if it
	 * is set.
	 */
	char	fqdn[STRLEN];
	char	ip[STRLEN];

	char	key[STRLEN];	/* ssh key */
};

enum {
	STATE_FLAGS_QUIT	= (1 << 0),
	STATE_FLAGS_SCREEN_IS_OUTDATED	= (1 << 1)
};

/*
 * Application state.
 */
struct state {
	int		argc;
	char		**argv;

	int		num_entries;
	struct entry	*entries;

	int		choice;

	int		ch;
	uint64_t	flags;
};

static int fill_localhost_entry(struct entry *localhost)
{
	*((char *)mempcpy(localhost->name, "localhost", STRLEN-1)) = 0x0;
	*((char *)mempcpy(localhost->host, "localhost", STRLEN-1)) = 0x0;

	*localhost->user = 0x0;
	getlogin_r(localhost->user, STRLEN);	/* ignore error */

	*localhost->fqdn = 0x0;
	*localhost->ip = 0x0;
	*localhost->key = 0x0;

	*((char *)mempcpy(localhost->descr, "Execute shell on localhost.", STRLEN-1)) = 0x0;

	return 0;
}

static FILE *open_rc_file()
{
	int n, m;
	char path[1024];
	const char *home;
	const char *fname = "/" RCFILE;

	home = getenv("HOME");
	if (unlikely(!home))
		home = "";

	n = strlen(home);
	m = strlen(fname);

	if (unlikely(n + m + 1 > sizeof(path)))
		return NULL;

	*((char* )mempcpy(mempcpy(path, home, n), fname, m)) = 0x0;

	return fopen(path, "r");
}

static int count_entries_in_file(FILE *fp)
{
	int count;
	int ch;

	/* Missing files are treated like empty ones here
	 * for convenience. */
	if (unlikely(!fp))
		return 0;

	fseek(fp, 0, SEEK_SET);

	count = 0;
	while (1) {
		ch = fgetc(fp);
		
		if ('\n' == ch)
			++count;
		
		if (';' == ch) {
			while ((ch != EOF) && ('\n' != ch)) {
				ch = fgetc(fp);
			}
		}
		
		if (EOF == ch)
			break;
	}

	if (unlikely(count % 7)) {
		fprintf(stderr, "Invalid input file (count = %d)\n", count);
		return -1;
	}

	return count / 7;
}

static int line(FILE* fp, char *buffer)
{
	int ch;
	int i;

	while (1) {
	        ch = fgetc(fp);

	        if (';' != ch)
			break;

		while ((ch != EOF) && ('\n' != ch)) {
			ch = fgetc(fp);
		}
	}

	i = 0;

	while ((ch != EOF) && ('\n' != ch)) {
		if (('\n' != ch) && (i < STRLEN))
			buffer[i++] = ch;
		ch = fgetc(fp);
	}

	buffer[i] = 0x0;

	return 0;
}

static int read_entries_from_file(FILE* fp, int n, struct entry *entries)
{
	int i;

	if (unlikely(!fp))
		return 0;
	
	fseek(fp, 0, SEEK_SET);

	for (i = 0; i < n; ++i) {
		line(fp, entries[i].name);
		line(fp, entries[i].host);
		line(fp, entries[i].user);
		line(fp, entries[i].descr);
		line(fp, entries[i].fqdn);
		line(fp, entries[i].ip);
		line(fp, entries[i].key);
	}

	return 0;
} 

static int fill_entries(struct state *state)
{
	FILE *fp;
	int ret = 1;

	state->num_entries = 0;
	state->entries     = NULL;

	fp = open_rc_file();
	
	state->num_entries = count_entries_in_file(fp);
	if (unlikely(state->num_entries < 0)) {
		ret = 1;
		goto out;
	}

	/* localhost */
	++state->num_entries;

	state->entries = malloc(state->num_entries*sizeof(struct entry));
	if (unlikely(!state->entries)) {
		ret = 1;
		goto out;
	}

	fill_localhost_entry(&state->entries[0]);
	
	ret = read_entries_from_file(fp, state->num_entries-1, 
	                             &state->entries[1]);

out:
	if (fp)
		fclose(fp);
	return ret;
}

static char *merge(const char *str1, char ch, const char *str2)
{
	char *str;
	char *tmp;

	str = malloc(2*STRLEN + 1);
	if (unlikely(!str))
		return NULL;

	tmp = mempcpy(str, str1, strlen(str1));
	*tmp = ch;
	mempcpy(tmp + 1, str2, strlen(str2));

	return str;
}

static int ssh(const struct state *state)
{
	char *argv[MAX_ARGS];
	int i;
	const struct entry *entry = &state->entries[state->choice-1];
	char *str1;
	char *str2;
	const char *exe;

	i = 0;
	memset(argv, 0, sizeof(argv));

	/* handle the localhost seperately */
	if (1 == state->choice) {
		exe = "/bin/bash";
	} else {
		argv[i++] = strdup("ssh");

		if (strlen(entry->key)) {
			argv[i++] = strdup("-i");
			argv[i++] = strdup(entry->key);
		}

		str1 = NULL;
		if (strlen(entry->user) > 0)
			str1 = entry->user;

		str2 = NULL;
		if (strlen(entry->fqdn) > 0)
			str2 = entry->fqdn;
		else if (strlen(entry->ip) > 0)
			str2 = entry->ip;
		else
			str2 = entry->host;

		argv[i++] = merge(str1, '@', str2);
		argv[i++] = NULL;

		exe = SSH;
	}

	return execv(exe, argv);
}

static int render(struct state *state)
{
	int posy = 0;
	int i;
	
	clear();

	mvprintw(posy++, 0, "%s", state->argv[0]);
	mvprintw(posy++, 0, "");

	attron(COLOR_PAIR(2));
	mvprintw(posy++, 0, " %4s %-16s %-16s %-32s %-32s",
	         "NUM",
	         "NAME",
	         "USER",
	         "HOST",
	         "DESCRIPTION");
	attroff(COLOR_PAIR(2));

	for (i = 0; i < state->num_entries; ++i) {
		if ((i+1) == state->choice)
			attron(COLOR_PAIR(3));

		mvprintw(posy++, 0, " %4d %-16s %-16s %-32s %-32s", 
		                    i + 1,
		                    state->entries[i].name,
		                    state->entries[i].user,
		                    state->entries[i].host,
		                    state->entries[i].descr);

		if ((i+1) == state->choice)
			attroff(COLOR_PAIR(3));
	}

	move(1, 0);

	refresh();

	return 0;
}

static int loop(struct state *state)
{
	int quit = 0;

	do {
		state->ch = getch();

		if (KEY_F(1) == state->ch) {
			state->flags |= STATE_FLAGS_QUIT;
			return 0;
		}

		switch (state->ch) {
		case KEY_RESIZE:
			state->flags |= STATE_FLAGS_SCREEN_IS_OUTDATED;
		case KEY_MOUSE:
			break;
		case KEY_DOWN:
			if (state->choice < state->num_entries) {
				++state->choice;
				state->flags |= STATE_FLAGS_SCREEN_IS_OUTDATED;
			}
			break;
		case KEY_UP:
			if (state->choice > 1) {
				--state->choice;
				state->flags |= STATE_FLAGS_SCREEN_IS_OUTDATED;
			}
			break;
		case 0xa:	// return/enter
			quit = 1;
			break;
		}

		if (state->flags &= STATE_FLAGS_SCREEN_IS_OUTDATED) {
			render(state);
			state->flags ^= STATE_FLAGS_SCREEN_IS_OUTDATED;
		}
	} while(!quit);
	
	return 0;
}


int main(int argc, char **argv)
{
	struct state state = {
		.choice = 1
	};
	int ret;

	state.argc = argc;
	state.argv = argv;

	ret = fill_entries(&state);
	if (unlikely(ret)) {
		fprintf(stderr, "Could not read rc file.\n");
		return 1;
	}

	initscr();
	
	start_color();
	init_pair(1, COLOR_BLACK, COLOR_WHITE);
	init_pair(2, COLOR_BLACK, COLOR_GREEN);
	init_pair(3, COLOR_BLACK, COLOR_CYAN);

	use_default_colors();

	clear();
	noecho();
	keypad(stdscr, TRUE);

	/* Initial rendering */
	render(&state);

	loop(&state);

	endwin();

	if (state.flags & STATE_FLAGS_QUIT) {
		/* No cleanup of state necessary. */
		return 1;
	}

	return ssh(&state);
}

